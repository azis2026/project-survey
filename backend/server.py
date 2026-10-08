from dotenv import load_dotenv
load_dotenv()

import asyncio
import base64
import csv
import hashlib
import hmac
import io
import ipaddress
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import bcrypt
import httpx
import jwt
import qrcode
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import Workbook
from pydantic import BaseModel, EmailStr, Field, field_validator

MONGO_URL = (
    os.environ.get("MONGO_URL")
    or os.environ.get("MONGODB_URI")
    or os.environ.get("MONGO_PRIVATE_URL")
    or os.environ.get("DATABASE_URL")
    or "mongodb://localhost:27017"
)
DB_NAME = os.environ.get("DB_NAME", "survey_db")
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-key-change-in-production")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@survey.local").lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminSurvey2026!")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
EMERGENT_EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Survey Kepuasan Layanan")
WEBHOOK_CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET", secrets.token_hex(16))
EMAIL_BASE_URL = "https://integrations.emergentagent.com"

# Parse multiple or single FRONTEND_URL origins cleanly
allowed_origins = [o.strip().rstrip("/") for o in FRONTEND_URL.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
app = FastAPI(title="Survey Kepuasan Layanan")
api = APIRouter(prefix="/api")
LABELS = {1: "Sangat Tidak Puas", 2: "Tidak Puas", 3: "Cukup Puas", 4: "Puas", 5: "Sangat Puas"}
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.up\.railway\.app|https://.*\.railway\.app|https://.*\.hf\.space|https://.*\.github\.io|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or f"survey-{uuid.uuid4().hex[:6]}"

class LoginIn(BaseModel):
    email: str
    password: str

class ResponseIn(BaseModel):
    survey_id: str
    rating: int
    comment: str = ""
    @field_validator("rating")
    @classmethod
    def valid_rating(cls, value):
        if value not in range(1, 6): raise ValueError("Rating harus antara 1 dan 5")
        return value
    @field_validator("comment")
    @classmethod
    def valid_comment(cls, value):
        if len(value) > 500: raise ValueError("Komentar maksimal 500 karakter")
        return value.strip()

class SurveyIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=3, max_length=300)
    question: str = Field(min_length=3, max_length=180)
    comment_placeholder: str = Field(min_length=3, max_length=120)
    max_comment_length: int = Field(default=500, ge=50, le=2000)
    status: str = "active"
    slug: Optional[str] = None

class UserIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=120)
    role: str = "admin"
    @field_validator("role")
    @classmethod
    def valid_role(cls, value):
        if value not in {"admin", "super_admin"}: raise ValueError("Role tidak valid")
        return value

class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=120)
    new_password: str = Field(min_length=8, max_length=120)

class BrandingIn(BaseModel):
    institution_name: str = Field(min_length=2, max_length=120)
    accent_color: str = Field(default="#2563eb")
    logo_data_url: Optional[str] = None
    digest_recipient: Optional[EmailStr] = None
    @field_validator("accent_color")
    @classmethod
    def hex_color(cls, value):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value): raise ValueError("Warna harus format HEX, mis. #2563eb")
        return value.lower()
    @field_validator("logo_data_url")
    @classmethod
    def check_logo(cls, value):
        if value is None or value == "": return None
        # P3 hardening: restrict logo to raster image mime types; reject SVG (defense-in-depth).
        allowed = ("data:image/png;", "data:image/jpeg;", "data:image/webp;", "data:image/gif;")
        if not value.startswith(allowed): raise ValueError("Logo harus PNG, JPEG, WebP, atau GIF")
        if len(value) > 400_000: raise ValueError("Ukuran logo maksimal 300KB")
        return value

def sanitize_cell(value):
    # SEC-002: Prevent CSV/XLSX formula injection from attacker-controlled text.
    if value is None: return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        text = "'" + text
    return text

def now(): return datetime.now(timezone.utc).isoformat()
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())
def token_for(email): return jwt.encode({"sub": email, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, JWT_SECRET, algorithm="HS256")

async def current_admin(request: Request):
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token: raise HTTPException(401, "Sesi admin diperlukan")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = await db.users.find_one({"email": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user or user.get("role") not in {"admin", "super_admin"}: raise HTTPException(401, "Sesi admin tidak valid")
        return user
    except (jwt.PyJWTError, KeyError): raise HTTPException(401, "Sesi admin telah berakhir")

async def super_admin(user=Depends(current_admin)):
    if user.get("role") != "super_admin": raise HTTPException(403, "Khusus super admin")
    return user

async def seed():
    await db.users.create_index("email", unique=True)
    await db.surveys.create_index("slug", unique=True)
    await db.responses.create_index([("survey_id", 1), ("created_at", -1)])
    await db.responses.create_index("rating")
    await db.login_attempts.create_index("identifier", unique=True)
    survey = await db.surveys.find_one({"slug": "pelayanan-umum"})
    if not survey:
        survey = {"id": str(uuid.uuid4()), "slug": "pelayanan-umum", "title": "Bagaimana Pengalaman Pelayanan Anda?", "description": "Berikan penilaian Anda untuk membantu kami meningkatkan kualitas pelayanan.", "question": "Seberapa puas Anda dengan pelayanan kami?", "comment_placeholder": "Tuliskan saran atau komentar Anda di sini...", "max_comment_length": 500, "status": "active", "created_at": now(), "updated_at": now()}
        await db.surveys.insert_one(survey)
    admin = await db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": ADMIN_EMAIL, "name": "Admin Survey", "password_hash": hash_password(ADMIN_PASSWORD), "role": "super_admin", "created_at": now()})
    elif admin.get("role") != "super_admin":
        # Only ensure the seeded account retains super_admin role; never force-reset the password (SEC-001).
        await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"role": "super_admin"}})
    if not await db.branding.find_one({"id": "default"}):
        await db.branding.insert_one({"id": "default", "institution_name": "Survey Kepuasan Layanan", "accent_color": "#2563eb", "logo_data_url": None, "digest_recipient": None, "updated_at": now()})
    if await db.responses.count_documents({"is_demo": True}) == 0:
        comments = ["Pelayanannya sangat baik.", "Sudah cukup baik, terima kasih.", "Semoga prosesnya lebih cepat.", "Petugas ramah dan informatif.", "Mohon ruang tunggu lebih nyaman."]
        docs = []
        for i in range(80):
            rating = 5 if i < 48 else 4 if i < 68 else 3 if i < 76 else 2 if i < 79 else 1
            docs.append({"id": str(uuid.uuid4()), "survey_id": survey["id"], "rating": rating, "rating_label": LABELS[rating], "comment": comments[i % len(comments)], "created_at": (datetime.now(timezone.utc) - timedelta(days=i % 30, hours=i % 8)).isoformat(), "is_demo": True})
        await db.responses.insert_many(docs)

async def safe_seed():
    try:
        await seed()
    except Exception as e:
        logger.error(f"Startup seed error: {e}")

@app.on_event("startup")
async def startup():
    asyncio.create_task(safe_seed())

@api.get("/survey/{slug}")
async def get_survey(slug: str):
    survey = await db.surveys.find_one({"slug": slug}, {"_id": 0})
    if not survey:
        await safe_seed()
        survey = await db.surveys.find_one({"slug": slug}, {"_id": 0})
    if not survey: raise HTTPException(404, "Survey tidak ditemukan")
    return survey

@api.get("/branding")
async def get_branding_public():
    doc = await db.branding.find_one({"id": "default"}, {"_id": 0, "digest_recipient": 0}) or {}
    return {"institution_name": doc.get("institution_name", "Survey Kepuasan Layanan"), "accent_color": doc.get("accent_color", "#2563eb"), "logo_data_url": doc.get("logo_data_url")}

@api.post("/responses")
async def submit_response(payload: ResponseIn, request: Request):
    survey = await db.surveys.find_one({"id": payload.survey_id}, {"_id": 0})
    if not survey or survey["status"] != "active": raise HTTPException(400, "Survey sedang tidak tersedia")
    ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(f"{ip}:{JWT_SECRET}".encode()).hexdigest()
    recent = await db.responses.count_documents({"survey_id": payload.survey_id, "ip_hash": ip_hash, "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()}})
    if recent: raise HTTPException(429, "Silakan tunggu sebentar sebelum mengirim kembali")
    doc = {"id": str(uuid.uuid4()), "survey_id": payload.survey_id, "rating": payload.rating, "rating_label": LABELS[payload.rating], "comment": payload.comment, "created_at": now(), "ip_hash": ip_hash, "is_demo": False}
    await db.responses.insert_one(doc)
    return {"ok": True, "id": doc["id"]}

@api.post("/auth/login")
async def login(payload: LoginIn, response: Response, request: Request):
    email = payload.email.lower()
    identifier = email
    attempt = await db.login_attempts.find_one({"identifier": identifier}, {"_id": 0})
    if attempt and attempt.get("locked_until", "") > now(): raise HTTPException(429, "Terlalu banyak percobaan. Coba lagi dalam 15 menit.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        failures = (attempt.get("failures", 0) if attempt else 0) + 1
        update = {"identifier": identifier, "failures": failures, "updated_at": now()}
        if failures >= 5: update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
        raise HTTPException(401, "Username atau password salah.")
    await db.login_attempts.delete_one({"identifier": identifier})
    token = token_for(user["email"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=28800, path="/")
    return {"token": token, "email": user["email"], "name": user["name"], "role": user["role"]}

@api.post("/auth/logout")
async def logout(response: Response): response.delete_cookie("access_token", path="/", samesite="none", secure=True); return {"ok": True}

@api.get("/auth/me")
async def me(user=Depends(current_admin)): return user

@api.post("/auth/change-password")
async def change_password(payload: PasswordChangeIn, user=Depends(current_admin)):
    doc = await db.users.find_one({"email": user["email"]})
    if not doc or not verify_password(payload.current_password, doc["password_hash"]):
        raise HTTPException(400, "Password lama tidak sesuai.")
    await db.users.update_one({"email": user["email"]}, {"$set": {"password_hash": hash_password(payload.new_password), "password_changed_at": now()}})
    return {"ok": True}

def date_match(doc, period, start_iso=None, end_iso=None):
    if period == "custom":
        if start_iso and doc["created_at"] < start_iso: return False
        if end_iso and doc["created_at"] > end_iso: return False
        return True
    if period == "all": return True
    days = {"today": 1, "7d": 7, "30d": 30, "month": 31}.get(period, 30)
    return doc["created_at"] >= (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

def date_bounds(start_date, end_date):
    start_iso = None
    end_iso = None
    if start_date:
        try: start_iso = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc).isoformat()
        except ValueError: raise HTTPException(400, "Format start_date tidak valid")
    if end_date:
        try: end_iso = (datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)).isoformat()
        except ValueError: raise HTTPException(400, "Format end_date tidak valid")
    return start_iso, end_iso

async def filtered_responses(period="all", rating=None, survey_id=None, start_date=None, end_date=None):
    query = {"survey_id": survey_id} if survey_id else {}
    docs = await db.responses.find(query, {"_id": 0, "ip_hash": 0}).sort("created_at", -1).to_list(10000)
    start_iso, end_iso = date_bounds(start_date, end_date)
    return [d for d in docs if date_match(d, period, start_iso, end_iso) and (not rating or d["rating"] == rating)]

@api.get("/admin/analytics")
async def analytics(period: str = "all", survey_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(current_admin)):
    docs = await filtered_responses(period, survey_id=survey_id, start_date=start_date, end_date=end_date)
    total = len(docs)
    counts = {str(i): sum(1 for d in docs if d["rating"] == i) for i in range(1, 6)}
    avg = round(sum(d["rating"] for d in docs) / total, 2) if total else 0
    trend = {}
    for d in docs: trend[d["created_at"][:10]] = trend.get(d["created_at"][:10], 0) + d["rating"]
    trend_data = [{"date": key[5:], "rating": round(value / sum(1 for d in docs if d["created_at"][:10] == key), 2)} for key, value in sorted(trend.items())]
    return {"total": total, "average": avg, "comments": sum(1 for d in docs if d["comment"]), "five_percent": round(counts["5"] / total * 100) if total else 0, "counts": counts, "trend": trend_data[-30:], "recent": docs[:5]}

@api.get("/admin/responses")
async def responses(page: int = 1, limit: int = 10, search: str = "", rating: Optional[int] = None, period: str = "all", survey_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(current_admin)):
    docs = await filtered_responses(period, rating, survey_id, start_date, end_date)
    search = search.lower()
    if search: docs = [d for d in docs if search in d.get("comment", "").lower() or search in d["rating_label"].lower()]
    start = (page - 1) * limit
    return {"items": docs[start:start + limit], "total": len(docs), "page": page, "pages": max(1, (len(docs) + limit - 1) // limit)}

@api.get("/admin/responses/{response_id}")
async def response_detail(response_id: str, user=Depends(current_admin)):
    doc = await db.responses.find_one({"id": response_id}, {"_id": 0, "ip_hash": 0})
    if not doc: raise HTTPException(404, "Data tidak ditemukan")
    return doc

# ------- SURVEYS -------
@api.get("/admin/surveys")
async def list_surveys(user=Depends(current_admin)):
    docs = await db.surveys.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    ids = [d["id"] for d in docs]
    counts = {}
    if ids:
        pipeline = [{"$match": {"survey_id": {"$in": ids}}}, {"$group": {"_id": "$survey_id", "count": {"$sum": 1}, "avg": {"$avg": "$rating"}}}]
        async for row in db.responses.aggregate(pipeline):
            counts[row["_id"]] = {"count": row["count"], "avg": round(row["avg"], 2)}
    for doc in docs:
        doc["response_count"] = counts.get(doc["id"], {}).get("count", 0)
        doc["average_rating"] = counts.get(doc["id"], {}).get("avg", 0)
    return docs

@api.post("/admin/surveys")
async def create_survey(payload: SurveyIn, user=Depends(current_admin)):
    slug = slugify(payload.slug or payload.title)
    if await db.surveys.find_one({"slug": slug}): raise HTTPException(400, "Slug sudah digunakan, pilih yang lain.")
    doc = {"id": str(uuid.uuid4()), "slug": slug, "title": payload.title, "description": payload.description, "question": payload.question, "comment_placeholder": payload.comment_placeholder, "max_comment_length": payload.max_comment_length, "status": payload.status, "created_at": now(), "updated_at": now()}
    await db.surveys.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.put("/admin/surveys/{survey_id}")
async def update_survey(survey_id: str, payload: SurveyIn, user=Depends(current_admin)):
    existing = await db.surveys.find_one({"id": survey_id})
    if not existing: raise HTTPException(404, "Survey tidak ditemukan")
    update = {"title": payload.title, "description": payload.description, "question": payload.question, "comment_placeholder": payload.comment_placeholder, "max_comment_length": payload.max_comment_length, "status": payload.status, "updated_at": now()}
    if payload.slug and payload.slug != existing["slug"]:
        new_slug = slugify(payload.slug)
        if await db.surveys.find_one({"slug": new_slug, "id": {"$ne": survey_id}}): raise HTTPException(400, "Slug sudah digunakan.")
        update["slug"] = new_slug
    await db.surveys.update_one({"id": survey_id}, {"$set": update})
    return await db.surveys.find_one({"id": survey_id}, {"_id": 0})

@api.delete("/admin/surveys/{survey_id}")
async def delete_survey(survey_id: str, user=Depends(current_admin)):
    count = await db.surveys.count_documents({})
    if count <= 1: raise HTTPException(400, "Minimal satu survey harus tetap tersedia.")
    survey = await db.surveys.find_one({"id": survey_id})
    if not survey: raise HTTPException(404, "Survey tidak ditemukan")
    await db.responses.delete_many({"survey_id": survey_id})
    await db.surveys.delete_one({"id": survey_id})
    return {"ok": True}

@api.get("/admin/settings")
async def settings(user=Depends(current_admin)):
    return await db.surveys.find_one({"slug": "pelayanan-umum"}, {"_id": 0}) or await db.surveys.find_one({}, {"_id": 0})

@api.put("/admin/settings")
async def update_settings(payload: SurveyIn, user=Depends(current_admin)):
    target = await db.surveys.find_one({"slug": "pelayanan-umum"}) or await db.surveys.find_one({})
    if not target: raise HTTPException(404, "Survey tidak ditemukan")
    return await update_survey(target["id"], payload, user)

@api.delete("/admin/demo-data")
async def clear_demo(user=Depends(current_admin)):
    result = await db.responses.delete_many({"is_demo": True})
    return {"deleted": result.deleted_count}

# ------- USERS (super admin only) -------
@api.get("/admin/users")
async def list_users(user=Depends(super_admin)):
    docs = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(100)
    return docs

@api.post("/admin/users")
async def create_user(payload: UserIn, user=Depends(super_admin)):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}): raise HTTPException(400, "Email sudah terdaftar.")
    doc = {"id": str(uuid.uuid4()), "email": email, "name": payload.name, "password_hash": hash_password(payload.password), "role": payload.role, "created_at": now()}
    await db.users.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "password_hash" and k != "_id"}

@api.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, user=Depends(super_admin)):
    target = await db.users.find_one({"id": user_id})
    if not target: raise HTTPException(404, "Pengguna tidak ditemukan")
    if target["email"] == user["email"]: raise HTTPException(400, "Tidak bisa menghapus akun yang sedang login.")
    if target["email"] == ADMIN_EMAIL: raise HTTPException(400, "Akun super admin utama tidak bisa dihapus.")
    await db.users.delete_one({"id": user_id})
    return {"ok": True}

# ------- BRANDING -------
@api.get("/admin/branding")
async def get_branding(user=Depends(current_admin)):
    doc = await db.branding.find_one({"id": "default"}, {"_id": 0})
    return doc or {}

@api.put("/admin/branding")
async def update_branding(payload: BrandingIn, user=Depends(super_admin)):
    update = payload.model_dump()
    update["updated_at"] = now()
    await db.branding.update_one({"id": "default"}, {"$set": update}, upsert=True)
    return await db.branding.find_one({"id": "default"}, {"_id": 0})

@api.get("/admin/qr/{slug}.png")
async def qr_png(slug: str, user=Depends(current_admin)):
    survey = await db.surveys.find_one({"slug": slug}, {"_id": 0})
    if not survey: raise HTTPException(404, "Survey tidak ditemukan")
    url = f"{FRONTEND_URL}/survey/{slug}"
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png", headers={"Content-Disposition": f'inline; filename="qr-{slug}.png"'})

@api.get("/admin/export.csv")
async def export_csv(period: str = "all", survey_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(current_admin)):
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["ID", "Tanggal", "Waktu", "Rating", "Label Rating", "Komentar"])
    for d in await filtered_responses(period, survey_id=survey_id, start_date=start_date, end_date=end_date):
        dt = datetime.fromisoformat(d["created_at"])
        writer.writerow([sanitize_cell(d["id"]), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"), d["rating"], sanitize_cell(d["rating_label"]), sanitize_cell(d["comment"])])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=survey-responses.csv"})

@api.get("/admin/export.xlsx")
async def export_xlsx(period: str = "all", survey_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user=Depends(current_admin)):
    wb = Workbook(); ws = wb.active; ws.title = "Responses"
    headers = ["ID", "Tanggal", "Waktu", "Rating", "Label Rating", "Komentar"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    widths = [34, 12, 10, 8, 20, 60]
    for i, w in enumerate(widths, 1): ws.column_dimensions[chr(64 + i)].width = w
    for d in await filtered_responses(period, survey_id=survey_id, start_date=start_date, end_date=end_date):
        dt = datetime.fromisoformat(d["created_at"])
        ws.append([sanitize_cell(d["id"]), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M"), d["rating"], sanitize_cell(d["rating_label"]), sanitize_cell(d["comment"])])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=survey-responses.xlsx"})

# ================= EMAIL (Emergent Resend proxy) =================
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv", "send us your password", "enter your password below", "confirm your card number", "your full card number", "seed phrase", "recovery phrase", "verify your card", "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)

def _host_ok(host):
    if not host or "xn--" in host: return False
    try: ipaddress.ip_address(host); return False
    except ValueError: pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)

def _same_site(shown, real):
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)

class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []
    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []
    def handle_data(self, data):
        if self._href is not None: self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []

def _assert_safe_email(subject, html):
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}: raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body: raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")): continue
        if not low.startswith("https://"): raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None: raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real: continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real): raise ValueError(f"Anchor text {m.group(1)!r} ≠ real link host {real!r} (G3)")

async def send_email(*, to, subject, html):
    if not EMERGENT_EMAIL_KEY:
        logger.info("EMERGENT_EMAIL_KEY is not set; skipping email dispatch.")
        return "skipped"
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            resp = await http_client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMERGENT_EMAIL_KEY}, json=payload)
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise

def build_digest_html(stats, brand_name, period_label):
    counts = stats["counts"]
    bar = lambda n: "█" * max(1, int(((counts.get(str(n), 0) / stats["total"]) if stats["total"] else 0) * 20))
    rows = "".join(f'<tr><td style="padding:6px 0;color:#334155">{"★"*n}{"☆"*(5-n)}</td><td style="padding:6px 12px;color:#64748b;font-family:monospace">{bar(n)}</td><td style="padding:6px 0;color:#0f172a;font-weight:700;text-align:right">{counts.get(str(n),0)}</td></tr>' for n in [5,4,3,2,1])
    comments = "".join(f'<li style="padding:6px 0;color:#334155;font-size:14px;line-height:1.6">“{escape(c["comment"][:160])}” <span style="color:#94a3b8">— {"★"*c["rating"]}</span></li>' for c in stats["recent"] if c.get("comment"))
    comments_block = f'<ul style="list-style:none;padding:0;margin:0">{comments}</ul>' if comments else '<p style="color:#64748b;font-size:13px">Belum ada komentar baru pada periode ini.</p>'
    return f'''<table role="presentation" width="100%" style="background:#f8fafc;padding:28px 0"><tr><td align="center"><table role="presentation" width="560" style="background:#ffffff;border-radius:14px;padding:34px;font-family:Arial,Helvetica,sans-serif;color:#0f172a"><tr><td><p style="margin:0;color:#2563eb;font-size:11px;font-weight:800;letter-spacing:.1em">REKAP MINGGUAN</p><h1 style="margin:8px 0 4px;font-size:24px;color:#0f172a">{escape(brand_name)}</h1><p style="margin:0;color:#64748b;font-size:13px">{escape(period_label)}</p></td></tr><tr><td style="padding-top:24px"><table role="presentation" width="100%" style="border-collapse:separate;border-spacing:8px"><tr><td style="background:#eff6ff;border-radius:10px;padding:16px;width:33%"><p style="margin:0;color:#1e40af;font-size:11px;font-weight:700">RESPONDEN</p><p style="margin:4px 0 0;font-size:22px;font-weight:800;color:#0f172a">{stats["total"]}</p></td><td style="background:#fef3c7;border-radius:10px;padding:16px;width:33%"><p style="margin:0;color:#92400e;font-size:11px;font-weight:700">RATA-RATA</p><p style="margin:4px 0 0;font-size:22px;font-weight:800;color:#0f172a">{stats["average"]} <span style="font-size:12px;color:#64748b">/5</span></p></td><td style="background:#dcfce7;border-radius:10px;padding:16px;width:33%"><p style="margin:0;color:#166534;font-size:11px;font-weight:700">RATING 5</p><p style="margin:4px 0 0;font-size:22px;font-weight:800;color:#0f172a">{stats["five_percent"]}%</p></td></tr></table></td></tr><tr><td style="padding-top:24px"><p style="margin:0 0 10px;font-size:14px;font-weight:700">Distribusi rating</p><table role="presentation" width="100%">{rows}</table></td></tr><tr><td style="padding-top:22px"><p style="margin:0 0 10px;font-size:14px;font-weight:700">Komentar terakhir</p>{comments_block}</td></tr><tr><td style="padding-top:28px;border-top:1px solid #e2e8f0"><p style="margin:16px 0 0;color:#94a3b8;font-size:11px">Email ini dikirim otomatis oleh {escape(brand_name)}. Kami tidak pernah meminta password atau data pribadi melalui email. Buka dashboard untuk melihat detail lengkap: <a href="{escape(FRONTEND_URL)}/admin" style="color:#2563eb">{escape(FRONTEND_URL)}/admin</a></p></td></tr></table></td></tr></table>'''

async def run_weekly_digest():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    docs = await db.responses.find({"created_at": {"$gte": start.isoformat(), "$lte": end.isoformat()}}, {"_id": 0, "ip_hash": 0}).sort("created_at", -1).to_list(10000)
    total = len(docs)
    counts = {str(i): sum(1 for d in docs if d["rating"] == i) for i in range(1, 6)}
    avg = round(sum(d["rating"] for d in docs) / total, 2) if total else 0
    stats = {"total": total, "average": avg, "five_percent": round(counts["5"] / total * 100) if total else 0, "counts": counts, "recent": docs[:5]}
    brand = await db.branding.find_one({"id": "default"}, {"_id": 0}) or {}
    brand_name = brand.get("institution_name") or "Survey Kepuasan Layanan"
    period_label = f"Periode {start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"
    html = build_digest_html(stats, brand_name, period_label)
    subject = f"Rekap Mingguan Survey — {end.strftime('%d %b %Y')}"
    recipients = set()
    if brand.get("digest_recipient"): recipients.add(brand["digest_recipient"].lower())
    async for u in db.users.find({"role": {"$in": ["admin", "super_admin"]}}, {"_id": 0, "email": 1}):
        if "@" in u["email"] and not u["email"].endswith(".local"): recipients.add(u["email"].lower())
    sent, errors = [], []
    for addr in recipients:
        try: sent.append(await send_email(to=addr, subject=subject, html=html))
        except Exception as e: errors.append(f"{addr}: {e}")
    await db.digest_runs.insert_one({"id": str(uuid.uuid4()), "run_at": now(), "total_responses": total, "recipients": list(recipients), "sent_ids": sent, "errors": errors})
    return {"recipients": list(recipients), "sent": len([s for s in sent if s]), "errors": errors, "total": total}

@api.post("/admin/digest/send-now")
async def digest_now(user=Depends(super_admin)):
    return await run_weekly_digest()

# ----- Cron webhook -----
# Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
@api.post("/cron/weekly-digest")
async def cron_weekly_digest(request: Request, background: BackgroundTasks, authorization: Optional[str] = Header(None), x_webhook_id: Optional[str] = Header(None)):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    expected = f"Bearer {WEBHOOK_CRON_SECRET}"
    if not authorization or not hmac.compare_digest(authorization, expected): raise HTTPException(401, "Unauthorized")
    run_id = x_webhook_id or str(uuid.uuid4())
    if await db.digest_runs.find_one({"run_id": run_id}): return {"ok": True, "status": "duplicate"}
    await db.digest_runs.insert_one({"run_id": run_id, "received_at": now()})
    background.add_task(run_weekly_digest)
    return {"ok": True, "status": "queued", "run_id": run_id}

@app.get("/")
async def root():
    return {"status": "ok", "app": "Survey Kepuasan Layanan API", "version": "1.0"}

@app.get("/health")
@api.get("/health")
async def health():
    db_status = "unknown"
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout=1.5)
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({type(e).__name__}: {e})"
    
    sanitized_url = re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", MONGO_URL) if MONGO_URL else ""
    return {
        "status": "ok",
        "database": db_status,
        "mongo_configured": bool(
            os.environ.get("MONGO_URL")
            or os.environ.get("MONGODB_URI")
            or os.environ.get("MONGO_PRIVATE_URL")
            or os.environ.get("DATABASE_URL")
        ),
        "mongo_target": sanitized_url,
    }

app.include_router(api)
logging.basicConfig(level=logging.INFO)

@app.on_event("shutdown")
async def shutdown(): client.close()

if __name__ == "__main__":
    import uvicorn
    raw_port = os.environ.get("PORT", "8000")
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        port = 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
