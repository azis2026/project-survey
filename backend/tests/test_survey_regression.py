"""Regression coverage for the public survey and protected admin API."""
import os

import pytest
import requests


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@survey.local"
ADMIN_PASSWORD = "AdminSurvey2026!"


@pytest.fixture(scope="module")
def client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_client(client):
    response = client.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "admin"
    assert response.cookies.get("access_token")
    return client


def test_public_survey_is_active_and_complete(client):
    response = client.get(f"{BASE_URL}/api/survey/pelayanan-umum")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "pelayanan-umum"
    assert body["status"] == "active"
    assert body["max_comment_length"] == 500


def test_response_validation_rejects_invalid_rating(client):
    response = client.post(f"{BASE_URL}/api/responses", json={"survey_id": "missing", "rating": 6, "comment": ""})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_admin_me_and_analytics_have_real_data(admin_client):
    me = admin_client.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL
    analytics = admin_client.get(f"{BASE_URL}/api/admin/analytics", params={"period": "all"})
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["total"] >= 80
    assert set(body["counts"]) == {"1", "2", "3", "4", "5"}
    assert isinstance(body["trend"], list)
    assert isinstance(body["recent"], list)


def test_responses_search_filter_pagination_and_detail(admin_client):
    response = admin_client.get(f"{BASE_URL}/api/admin/responses", params={"page": 1, "limit": 5, "rating": 5, "search": "baik"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 5
    assert body["page"] == 1
    assert body["pages"] >= 1
    if body["items"]:
        detail = admin_client.get(f"{BASE_URL}/api/admin/responses/{body['items'][0]['id']}")
        assert detail.status_code == 200
        assert detail.json()["id"] == body["items"][0]["id"]


def test_settings_roundtrip_and_csv_export(admin_client):
    current = admin_client.get(f"{BASE_URL}/api/admin/settings")
    assert current.status_code == 200
    settings = current.json()
    payload = {k: settings[k] for k in ["title", "description", "question", "comment_placeholder", "max_comment_length", "status"]}
    updated = admin_client.put(f"{BASE_URL}/api/admin/settings", json=payload)
    assert updated.status_code == 200
    assert updated.json()["title"] == settings["title"]
    export = admin_client.get(f"{BASE_URL}/api/admin/export.csv")
    assert export.status_code == 200
    assert "text/csv" in export.headers.get("content-type", "")
    assert export.text.startswith("ID,Tanggal,Waktu,Rating,Label Rating,Komentar")


def test_logout_invalidates_cookie(admin_client):
    response = admin_client.post(f"{BASE_URL}/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    me = admin_client.get(f"{BASE_URL}/api/auth/me")
    assert me.status_code == 401