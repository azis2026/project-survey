# Survey Kepuasan Layanan — PRD

## Problem Statement
A simple, mobile-first customer satisfaction survey web app accessed via QR Code. Replaces manual Google Form surveys. Visitors rate the service with 1–5 stars and optionally leave a comment (anonymous, no account needed). Admin has a secure dashboard to monitor responses, trends, and export data.

## User Personas
- **Public Respondent** — Anonymous visitor arriving via QR Code / shared link. Expects to complete the survey in 10–20 seconds on a phone.
- **Admin** — Authenticated staff managing survey content, viewing analytics, downloading CSV, and sharing the QR code.

## Core Requirements (static)
- Anonymous public submission (rating 1–5 + optional ≤500-char comment)
- Admin login (secured, cookie-based) with brute-force lockout
- Dashboard: Total Responden, Rata-rata, % Rating 5, Komentar
- Trend line chart + distribution bar chart
- Response table with search, rating filter, pagination, detail modal
- Survey settings management (title, question, description, placeholder, max length, status)
- QR Code page with downloadable QR for the survey URL
- CSV export of responses
- Mobile-first, responsive layout
- Rate-limit per IP hash on submission (20s cooldown)

## Architecture
- **Frontend**: React (CRA), react-router-dom, axios (`withCredentials`), Recharts, lucide-react icons, Tailwind-friendly CSS variables.
- **Backend**: FastAPI, Motor (async MongoDB), bcrypt, PyJWT. Routes under `/api`.
- **Database**: MongoDB collections — `users`, `surveys`, `responses`, `login_attempts`.
- **Auth**: HttpOnly `access_token` cookie (JWT HS256, 8h). Admin seeded from env on startup.
- **Security**: Password hashing (bcrypt), email-based brute-force lockout (5 fails → 15 min), IP-hashed cooldown on `/responses`, Pydantic input validation, server-side rating/comment validation.

## What's Been Implemented (2026-02-08)
- Public survey flow at `/` and `/survey/:slug` — Landing → Rating → Optional comment → Thank you (now shows the institution's logo, name, and accent color from branding)
- Admin login with brute-force lockout (per-email)
- Admin dashboard with period filter (today/7d/30d/month/all/**custom date range**), per-survey filter, KPI cards, trend line chart, distribution bars, "Hapus Data Demo" button
- Responses page with search, rating + per-survey filter, pagination, detail modal, export dropdown (CSV + XLSX)
- Settings page (edits the default survey)
- Kelola Survey (Multi Survey) page — list/create/edit/delete surveys, prevents deleting the last one
- QR Code page served from backend (local PNG via `qrcode` lib), per-survey selector, one-click download
- **Pengguna Admin page (super_admin only)** — create/delete regular admins or additional super admins; seed admin + logged-in user protected from deletion
- **Logo & Branding page (super_admin only)** — institution name, HEX accent color (`--brand` CSS var), base64 logo upload (max 300KB), optional weekly digest recipient email
- **Weekly digest email** — Monday 08:00 WIB cron hits `/api/cron/weekly-digest` (bearer-auth, idempotent via X-Webhook-Id); aggregates 7-day stats, sends branded HTML email via Emergent-managed Resend to the digest recipient + every admin with a deliverable email; Branding page has "Kirim rekap sekarang" for immediate preview
- Email helper passes the full `_assert_safe_email` G2/G3 guardrail gate
- Role-based access control: `super_admin` vs `admin` (routes + sidebar links hidden; direct URLs redirect)
- Backend endpoints (new in this iteration):
  - `GET /api/branding` (public) · `GET /api/admin/branding` · `PUT /api/admin/branding` (super_admin)
  - `GET /api/admin/users` · `POST /api/admin/users` · `DELETE /api/admin/users/{id}` (super_admin)
  - `POST /api/admin/digest/send-now` (super_admin) · `POST /api/cron/weekly-digest` (bearer webhook)
  - Analytics/responses/exports accept `start_date` & `end_date` when `period=custom`

## Prioritized Backlog
### P1
- Logo via Emergent Object Storage (currently base64 up to 300KB in Mongo)
- Scheduled export delivery (CSV/XLSX emailed weekly as attachment)

### P2
- Branding preview on live survey while editing
- Per-survey analytics panel on the Kelola Survey card
- Timezone configuration in Settings

### P3
- Captcha / stronger anti-spam
- Shareable public read-only dashboard links for leadership

## Credentials (dev)
See `/app/memory/test_credentials.md`.
