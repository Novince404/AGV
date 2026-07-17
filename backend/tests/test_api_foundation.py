from __future__ import annotations

from app.core.version import get_version
from app.repositories.memory import auth_store


def test_health_version_and_v1_openapi(client):
    assert client.get("/health/live").json() == {"status": "alive", "version": get_version()}
    version = client.get("/version").json()
    assert version["version"] == "3.0.0-beta.2"
    schema = client.get("/openapi.json").json()
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/agvs" in schema["paths"]
    assert "/api/v1/dispatches" in schema["paths"]
    assert "/auth/login" not in schema["paths"]


def test_cookie_session_is_hashed_and_legacy_api_is_deprecated(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "enterprise_operator_demo", "password": "operator123"},
    )
    assert response.status_code == 200
    assert "session_token" not in response.json()
    raw_cookie = client.cookies.get("agv_session")
    assert raw_cookie
    assert raw_cookie not in auth_store.sessions
    assert len(auth_store.sessions) == 1
    assert client.get("/api/v1/auth/me").json()["authenticated"] is True
    legacy = client.get("/auth/me")
    assert legacy.headers["Deprecation"] == "true"
    assert legacy.headers["Sunset"] == "v4.0.0"


def test_problem_details_for_unauthorized_write(client):
    response = client.post("/api/v1/agv/create", json={"x": 1, "y": 2})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 401
    assert body["code"] == "auth_login_required"
    assert body["request_id"]


def test_device_command_idempotency(operator_client):
    headers = {"Idempotency-Key": "test-command-0001"}
    body = {"command_type": "move_to", "parameters": {"x": 4, "y": 2, "speed": 1}}
    first = operator_client.post("/api/v1/agvs/AGV-1/commands", json=body, headers=headers)
    second = operator_client.post("/api/v1/agvs/AGV-1/commands", json=body, headers=headers)
    assert first.status_code == 202
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["command"]["id"] == second.json()["command"]["id"]

    conflict = operator_client.post(
        "/api/v1/agvs/AGV-1/commands",
        json={"command_type": "stop", "parameters": {}},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_key_payload_mismatch"


def test_task_creation_idempotency(operator_client):
    headers = {"Idempotency-Key": "task-create-key-0001"}
    body = {"start_x": 0, "start_y": 0, "end_x": 1, "end_y": 1, "grid_cols": 8, "grid_rows": 8}
    first = operator_client.post("/api/v1/task/create", json=body, headers=headers)
    second = operator_client.post("/api/v1/task/create", json=body, headers=headers)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["task"]["id"] == second.json()["task"]["id"]
