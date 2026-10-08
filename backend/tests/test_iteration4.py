"""Backend tests for iteration 4: multi-admin users, branding, weekly digest, cron, custom date range."""
import os
import uuid
import yaml
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
SUPER_EMAIL = "admin@survey.local"
SUPER_PASSWORD = "AdminSurvey2026!"

# Read cron secret directly from backend/.env
CRON_SECRET = None
with open("/app/backend/.env") as _f:
    for line in _f:
        if line.startswith("WEBHOOK_CRON_SECRET"):
            CRON_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
assert CRON_SECRET, "WEBHOOK_CRON_SECRET missing in backend/.env"


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def super_client():
    return _login(SUPER_EMAIL, SUPER_PASSWORD)


@pytest.fixture(scope="module")
def regular_admin_creds(super_client):
    """Create a regular admin and yield email/password; cleanup after."""
    email = f"test_regadmin_{uuid.uuid4().hex[:6]}@example.com"
    password = "RegularAdmin2026!"
    r = super_client.post(f"{BASE_URL}/api/admin/users", json={
        "email": email, "name": "TEST Reg Admin", "password": password, "role": "admin"
    })
    assert r.status_code in (200, 201), r.text
    uid = r.json()["id"]
    yield {"email": email, "password": password, "id": uid}
    super_client.delete(f"{BASE_URL}/api/admin/users/{uid}")


@pytest.fixture(scope="module")
def regular_client(regular_admin_creds):
    return _login(regular_admin_creds["email"], regular_admin_creds["password"])


# ---- Super admin role ----
def test_me_super_admin(super_client):
    r = super_client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == SUPER_EMAIL
    assert data["role"] == "super_admin"


# ---- Users CRUD ----
def test_list_users_super(super_client):
    r = super_client.get(f"{BASE_URL}/api/admin/users")
    assert r.status_code == 200
    users = r.json()
    assert any(u["email"] == SUPER_EMAIL for u in users)


def test_create_delete_user(super_client):
    email = f"test_crud_{uuid.uuid4().hex[:6]}@example.com"
    r = super_client.post(f"{BASE_URL}/api/admin/users", json={
        "email": email, "name": "TEST CRUD", "password": "Password123!", "role": "admin"
    })
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["email"] == email
    assert "password_hash" not in body
    uid = body["id"]
    # Duplicate rejected
    r2 = super_client.post(f"{BASE_URL}/api/admin/users", json={
        "email": email, "name": "Dup", "password": "Password123!", "role": "admin"
    })
    assert r2.status_code == 400
    # Delete
    r3 = super_client.delete(f"{BASE_URL}/api/admin/users/{uid}")
    assert r3.status_code == 200


def test_cannot_delete_seed_admin(super_client):
    users = super_client.get(f"{BASE_URL}/api/admin/users").json()
    seed = next(u for u in users if u["email"] == SUPER_EMAIL)
    r = super_client.delete(f"{BASE_URL}/api/admin/users/{seed['id']}")
    assert r.status_code == 400


# ---- RBAC: regular admin ----
def test_regular_admin_blocked_from_users(regular_client):
    r = regular_client.get(f"{BASE_URL}/api/admin/users")
    assert r.status_code == 403


def test_regular_admin_can_read_branding(regular_client):
    r = regular_client.get(f"{BASE_URL}/api/admin/branding")
    assert r.status_code == 200


def test_regular_admin_cannot_update_branding(regular_client):
    r = regular_client.put(f"{BASE_URL}/api/admin/branding", json={
        "institution_name": "Hacked", "accent_color": "#ff0000"
    })
    assert r.status_code == 403


def test_regular_admin_cannot_send_digest(regular_client):
    r = regular_client.post(f"{BASE_URL}/api/admin/digest/send-now")
    assert r.status_code == 403


# ---- Branding ----
def test_branding_public(super_client):
    r = requests.get(f"{BASE_URL}/api/branding")
    assert r.status_code == 200
    data = r.json()
    assert "institution_name" in data
    assert "accent_color" in data
    assert "digest_recipient" not in data


def test_branding_update_and_public_reflects(super_client):
    # Save current
    original = super_client.get(f"{BASE_URL}/api/admin/branding").json()
    try:
        new_name = f"TEST Inst {uuid.uuid4().hex[:4]}"
        payload = {
            "institution_name": new_name,
            "accent_color": "#10b981",
            "logo_data_url": None,
            "digest_recipient": "delivered@resend.dev"
        }
        r = super_client.put(f"{BASE_URL}/api/admin/branding", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["institution_name"] == new_name
        assert data["accent_color"] == "#10b981"
        # Public reflects
        pub = requests.get(f"{BASE_URL}/api/branding").json()
        assert pub["institution_name"] == new_name
        assert pub["accent_color"] == "#10b981"
    finally:
        # restore
        if original:
            restore = {
                "institution_name": original.get("institution_name") or "Survey Kepuasan Layanan",
                "accent_color": original.get("accent_color") or "#2563eb",
                "logo_data_url": original.get("logo_data_url"),
                "digest_recipient": original.get("digest_recipient"),
            }
            super_client.put(f"{BASE_URL}/api/admin/branding", json=restore)


def test_branding_invalid_color(super_client):
    r = super_client.put(f"{BASE_URL}/api/admin/branding", json={
        "institution_name": "X", "accent_color": "red"
    })
    assert r.status_code == 422


# ---- Custom date range analytics ----
def test_analytics_custom_date_range(super_client):
    r = super_client.get(f"{BASE_URL}/api/admin/analytics",
                         params={"period": "custom", "start_date": "2000-01-01", "end_date": "2000-01-02"})
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r2 = super_client.get(f"{BASE_URL}/api/admin/analytics",
                          params={"period": "custom", "start_date": "2020-01-01", "end_date": "2099-12-31"})
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1


def test_analytics_invalid_date(super_client):
    r = super_client.get(f"{BASE_URL}/api/admin/analytics",
                         params={"period": "custom", "start_date": "not-a-date"})
    assert r.status_code == 400


# ---- Cron webhook ----
def test_cron_no_auth():
    r = requests.post(f"{BASE_URL}/api/cron/weekly-digest")
    assert r.status_code == 401


def test_cron_wrong_bearer():
    r = requests.post(f"{BASE_URL}/api/cron/weekly-digest",
                      headers={"Authorization": "Bearer wrong-secret"})
    assert r.status_code == 401


def test_cron_correct_bearer_queues():
    wid = f"test-{uuid.uuid4().hex}"
    r = requests.post(f"{BASE_URL}/api/cron/weekly-digest",
                      headers={"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": wid})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["status"] == "queued"
    # Duplicate
    r2 = requests.post(f"{BASE_URL}/api/cron/weekly-digest",
                       headers={"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": wid})
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"


# ---- Send digest now ----
def test_digest_send_now_structure(super_client):
    # Make sure digest_recipient is delivered@resend.dev for a successful send
    original = super_client.get(f"{BASE_URL}/api/admin/branding").json()
    try:
        super_client.put(f"{BASE_URL}/api/admin/branding", json={
            "institution_name": original.get("institution_name") or "Survey Kepuasan Layanan",
            "accent_color": original.get("accent_color") or "#2563eb",
            "logo_data_url": original.get("logo_data_url"),
            "digest_recipient": "delivered@resend.dev"
        })
        r = super_client.post(f"{BASE_URL}/api/admin/digest/send-now")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "recipients" in body
        assert "sent" in body
        assert "errors" in body
        assert "delivered@resend.dev" in body["recipients"]
    finally:
        if original:
            super_client.put(f"{BASE_URL}/api/admin/branding", json={
                "institution_name": original.get("institution_name") or "Survey Kepuasan Layanan",
                "accent_color": original.get("accent_color") or "#2563eb",
                "logo_data_url": original.get("logo_data_url"),
                "digest_recipient": original.get("digest_recipient"),
            })


# ---- crons.yml ----
def test_crons_yml_valid():
    with open("/app/.emergent/crons.yml") as f:
        data = yaml.safe_load(f)
    assert "crons" in data
    cron = next(c for c in data["crons"] if c["name"] == "weekly-digest")
    assert cron["cron"] == "0 8 * * 1"
    assert cron["timezone"] == "Asia/Jakarta"
    assert "/api/cron/weekly-digest" in cron["endpoint"]
