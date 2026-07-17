from __future__ import annotations

from app.core.auth_rate_limit import LoginRateLimiter
from app.core.auth_security import _legacy_hash_password, password_needs_rehash, verify_password
from app.models.auth import AuthUser
from app.repositories.memory import auth_store


def test_legacy_password_is_upgraded_after_login(client):
    legacy_hash = _legacy_hash_password("legacy-password")
    auth_store.users.append(
        AuthUser(
            id="legacy-user",
            username="legacy-user",
            display_name="Legacy User",
            role="personal",
            password_hash=legacy_hash,
            active=True,
            builtin=False,
            account_status="approved",
        )
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "legacy-user", "password": "legacy-password"},
    )
    assert response.status_code == 200
    upgraded = auth_store.get_user_by_id("legacy-user").password_hash
    assert upgraded.startswith("$argon2id$")
    assert verify_password("legacy-password", upgraded)
    assert not password_needs_rehash(upgraded)


def test_login_rate_limiter_locks_after_five_failures():
    limiter = LoginRateLimiter(attempts=5, window_sec=900, lockout_sec=900)
    for _ in range(4):
        assert limiter.record_failure("account|source") == 0
    assert limiter.record_failure("account|source") == 900
    assert limiter.retry_after("account|source") > 0
    limiter.clear("account|source")
    assert limiter.retry_after("account|source") == 0


def test_forced_password_change_blocks_work_until_rotated(client):
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "enterprise_demo", "password": "enterprise123"},
    )
    assert admin_login.status_code == 200
    created = client.post(
        "/api/v1/auth/enterprise-members",
        json={
            "username": "new-operator",
            "password": "temporary-password-1",
            "display_name": "New Operator",
            "role": "enterprise_operator",
        },
    )
    assert created.status_code == 200, created.text
    client.post("/api/v1/auth/logout")
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "new-operator", "password": "temporary-password-1"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True
    blocked = client.post("/api/v1/agv/create", json={"x": 1, "y": 1})
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "auth_password_change_required"
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "temporary-password-1", "new_password": "replacement-password-2"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["user"]["must_change_password"] is False
    no_longer_password_blocked = client.post("/api/v1/agv/create", json={"x": 1, "y": 1})
    assert no_longer_password_blocked.json()["code"] != "auth_password_change_required"


def test_trial_cookie_write_requires_csrf(monkeypatch):
    from fastapi.testclient import TestClient

    from app.factory import create_app

    monkeypatch.setenv("AGV_APP_ENV", "trial")
    monkeypatch.setenv("AGV_DATA_BACKEND", "memory")
    monkeypatch.setenv("AGV_AUTH_DEMO_USERS_ENABLED", "true")
    monkeypatch.setenv("AGV_AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AGV_CSRF_ENABLED", "true")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "enterprise_operator_demo", "password": "operator123"},
        )
        assert login.status_code == 200
        blocked = client.post("/api/v1/agvs/AGV-8/commands", json={"command_type": "stop"})
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "csrf_validation_failed"
        accepted = client.post(
            "/api/v1/agvs/AGV-8/commands",
            json={"command_type": "stop"},
            headers={"X-CSRF-Token": client.cookies.get("agv_csrf")},
        )
        assert accepted.status_code == 202
