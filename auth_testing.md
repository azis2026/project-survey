# Auth Testing Playbook

Admin endpoint: `POST /api/auth/login` with email `admin@survey.local` and password `AdminSurvey2026!`.
Protected endpoint: `GET /api/auth/me` using the returned bearer token or cookie.
Logout endpoint: `POST /api/auth/logout`.
Public survey endpoint: `GET /api/survey/pelayanan-umum`.