"""Backend tests for new features: multi-survey CRUD, QR PNG, XLSX export, demo-data clear."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@survey.local"
ADMIN_PASSWORD = "AdminSurvey2026!"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return s


# --- Multi-Survey CRUD ---
def test_list_surveys(admin):
    r = admin.get(f"{BASE_URL}/api/admin/surveys")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    slugs = [s["slug"] for s in data]
    assert "pelayanan-umum" in slugs


def test_create_survey(admin):
    # cleanup if exists
    r = admin.get(f"{BASE_URL}/api/admin/surveys")
    for s in r.json():
        if s["slug"] == "test-pelayanan-admin":
            admin.delete(f"{BASE_URL}/api/admin/surveys/{s['id']}")
    payload = {
        "title": "TEST Pelayanan Administrasi",
        "slug": "test-pelayanan-admin",
        "description": "Testing survey",
        "question": "Bagaimana?",
        "comment_placeholder": "Komentar..",
        "max_comment_length": 300,
        "status": "active",
    }
    r = admin.post(f"{BASE_URL}/api/admin/surveys", json=payload)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["slug"] == "test-pelayanan-admin"
    assert "id" in body
    pytest.survey_id = body["id"]


def test_duplicate_slug_rejected(admin):
    r = admin.post(f"{BASE_URL}/api/admin/surveys", json={
        "title": "Dup Title", "slug": "test-pelayanan-admin", "description": "duplicate check",
        "question": "Bagaimana?", "comment_placeholder": "Komentar..", "max_comment_length": 100, "status": "active",
    })
    assert r.status_code == 400, r.text


def test_update_survey(admin):
    sid = pytest.survey_id
    r = admin.put(f"{BASE_URL}/api/admin/surveys/{sid}", json={
        "title": "TEST Updated Title", "slug": "test-pelayanan-admin", "description": "Testing survey",
        "question": "Bagaimana?", "comment_placeholder": "Komentar..",
        "max_comment_length": 300, "status": "active",
    })
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "TEST Updated Title"


def test_public_access_new_survey(admin):
    r = requests.get(f"{BASE_URL}/api/survey/test-pelayanan-admin")
    assert r.status_code == 200
    assert r.json()["slug"] == "test-pelayanan-admin"


def test_submit_response_to_new_survey(admin):
    sid = pytest.survey_id
    r = requests.post(f"{BASE_URL}/api/responses", json={
        "survey_id": sid, "rating": 5, "comment": "TEST response"
    })
    assert r.status_code in (200, 201), r.text


# --- QR PNG endpoint ---
def test_qr_png(admin):
    r = admin.get(f"{BASE_URL}/api/admin/qr/pelayanan-umum.png")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_qr_png_new_survey(admin):
    r = admin.get(f"{BASE_URL}/api/admin/qr/test-pelayanan-admin.png")
    assert r.status_code == 200
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_qr_png_unknown_slug(admin):
    r = admin.get(f"{BASE_URL}/api/admin/qr/this-does-not-exist.png")
    assert r.status_code == 404


# --- XLSX Export ---
def test_export_xlsx(admin):
    r = admin.get(f"{BASE_URL}/api/admin/export.xlsx")
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "spreadsheetml.sheet" in ct or "openxmlformats" in ct
    # XLSX starts with PK zip signature
    assert r.content[:2] == b"PK"


def test_export_csv_still_works(admin):
    r = admin.get(f"{BASE_URL}/api/admin/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# --- Analytics + Responses with survey_id filter ---
def test_analytics_with_survey_filter(admin):
    sid = pytest.survey_id
    r = admin.get(f"{BASE_URL}/api/admin/analytics", params={"period": "all", "survey_id": sid})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_responses_with_survey_filter(admin):
    sid = pytest.survey_id
    r = admin.get(f"{BASE_URL}/api/admin/responses", params={"survey_id": sid})
    assert r.status_code == 200


# --- Delete survey ---
def test_delete_survey(admin):
    sid = pytest.survey_id
    r = admin.delete(f"{BASE_URL}/api/admin/surveys/{sid}")
    assert r.status_code in (200, 204)


def test_delete_last_survey_blocked(admin):
    r = admin.get(f"{BASE_URL}/api/admin/surveys")
    surveys = r.json()
    # delete all but one
    ids_to_delete = [s["id"] for s in surveys[:-1]]
    for sid in ids_to_delete:
        admin.delete(f"{BASE_URL}/api/admin/surveys/{sid}")
    # now there should be exactly 1
    surveys = admin.get(f"{BASE_URL}/api/admin/surveys").json()
    assert len(surveys) == 1
    last = surveys[0]
    r = admin.delete(f"{BASE_URL}/api/admin/surveys/{last['id']}")
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "Minimal satu survey" in detail or "minimal" in detail.lower()


# --- Demo data clear (run last) ---
def test_clear_demo_data(admin):
    before = admin.get(f"{BASE_URL}/api/admin/analytics", params={"period": "all"}).json()["total"]
    r = admin.delete(f"{BASE_URL}/api/admin/demo-data")
    assert r.status_code == 200
    after = admin.get(f"{BASE_URL}/api/admin/analytics", params={"period": "all"}).json()["total"]
    assert after < before, f"Demo not cleared: before={before}, after={after}"
