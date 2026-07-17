from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE_DB_PATH = BACKEND_DIR / "agv_feedback_notification_smoke.db"
HOST = "127.0.0.1"
PORT = 8012
BASE_URL = f"http://{HOST}:{PORT}"
SMOKE_DB_URL = f"sqlite:///{SMOKE_DB_PATH.as_posix()}"


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def cleanup_db_file() -> None:
    if not SMOKE_DB_PATH.exists():
        return
    for _ in range(10):
        try:
            SMOKE_DB_PATH.unlink()
            return
        except PermissionError:
            time.sleep(0.2)


def build_server_env() -> dict[str, str]:
    env = os.environ.copy()
    env["AGV_DATA_BACKEND"] = "sqlite"
    env["AGV_DATABASE_URL"] = SMOKE_DB_URL
    env["AGV_DATABASE_AUTO_CREATE"] = "true"
    env["AGV_SERVE_FRONTEND_DIST"] = "false"
    env["AGV_HOST"] = HOST
    env["AGV_PORT"] = str(PORT)
    return env


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str | None = None,
) -> tuple[int, object]:
    headers = {}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=4) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else None
            return int(response.status), data
    except error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8")
            data = json.loads(raw) if raw else {"detail": raw}
        except Exception:
            data = {"detail": exc.reason}
        return int(exc.code), data


def wait_for_server_ready(process: subprocess.Popen[str]) -> None:
    last_error: Exception | None = None
    for _ in range(40):
        if process.poll() is not None:
            break
        try:
            root_status, _ = request_json("/")
            auth_status, auth_payload = request_json("/auth/me")
            if root_status == 200 and auth_status == 200 and isinstance(auth_payload, dict):
                return
        except Exception as exc:  # pragma: no cover - transient startup loop
            last_error = exc
        time.sleep(0.5)

    if process.poll() is not None:
        output = ""
        if process.stdout is not None:
            output = process.stdout.read()
        raise RuntimeError(f"feedback notification smoke backend exited early.\n{output}".strip())
    raise RuntimeError(f"feedback notification smoke backend did not become ready in time: {last_error}")


def login_token(username: str, password: str) -> str:
    response_status, response_payload = request_json(
        "/auth/login",
        method="POST",
        payload={
            "username": username,
            "password": password,
        },
    )
    expect(response_status == 200, f"login failed for {username}: {response_payload}")
    expect(isinstance(response_payload, dict), f"login payload invalid for {username}")
    token = str(response_payload.get("session_token") or "").strip()
    expect(token, f"login response missing session token for {username}")
    return token


def assert_enterprise_request_visibility() -> None:
    operator_token = login_token("enterprise_operator_demo", "operator123")
    logistics_token = login_token("enterprise_logistics_demo", "logistics123")
    admin_token = login_token("enterprise_demo", "enterprise123")
    personal_token = login_token("personal_demo", "personal123")

    recipient_status, recipient_payload = request_json("/feedback/enterprise/recipients", token=operator_token)
    expect(recipient_status == 200, f"enterprise recipient feed failed: {recipient_payload}")
    expect(isinstance(recipient_payload, dict), "enterprise recipient payload invalid")
    recipients = recipient_payload.get("items") or []
    logistics_user = next((item for item in recipients if str(item.get("role") or "") == "enterprise_logistics"), None)
    expect(logistics_user is not None, "enterprise request smoke could not find the logistics recipient")

    create_status, create_payload = request_json(
        "/feedback/enterprise/requests",
        method="POST",
        token=operator_token,
        payload={
            "category": "error",
            "title": "Smoke enterprise request",
            "content": "Verify that the target enterprise role can see the new request.",
            "target_user_id": str(logistics_user["id"]),
        },
    )
    expect(create_status == 200, f"enterprise request creation failed: {create_payload}")
    expect(isinstance(create_payload, dict), "enterprise request creation payload invalid")
    created_item = create_payload.get("item") or {}
    request_id = int(created_item.get("id") or 0)
    expect(request_id > 0, "enterprise request creation did not return a valid request id")

    logistics_status, logistics_payload = request_json("/feedback/enterprise/requests", token=logistics_token)
    expect(logistics_status == 200, f"logistics enterprise request feed failed: {logistics_payload}")
    expect(isinstance(logistics_payload, dict), "logistics enterprise request payload invalid")
    expect(
        any(int(item.get("id") or 0) == request_id for item in logistics_payload.get("items") or []),
        "target logistics role could not see the newly created enterprise request",
    )
    expect(
        int((logistics_payload.get("summary") or {}).get("open") or 0) >= 1,
        "target logistics role summary did not reflect the new open request",
    )

    admin_status, admin_payload = request_json("/feedback/enterprise/requests", token=admin_token)
    expect(admin_status == 200, f"enterprise admin request feed failed: {admin_payload}")
    expect(isinstance(admin_payload, dict), "enterprise admin request payload invalid")
    expect(
        any(int(item.get("id") or 0) == request_id for item in admin_payload.get("items") or []),
        "enterprise admin could not see the newly created enterprise request",
    )

    personal_status, personal_payload = request_json("/feedback/enterprise/requests", token=personal_token)
    expect(personal_status == 403, f"personal account should not access enterprise request feed: {personal_payload}")

    update_status, update_payload = request_json(
        f"/feedback/enterprise/requests/{request_id}/status",
        method="POST",
        token=logistics_token,
        payload={
            "status": "in_progress",
            "response_note": "Logistics acknowledged the request.",
        },
    )
    expect(update_status == 200, f"enterprise request status update failed: {update_payload}")

    refreshed_admin_status, refreshed_admin_payload = request_json("/feedback/enterprise/requests", token=admin_token)
    expect(refreshed_admin_status == 200, f"enterprise admin refresh feed failed: {refreshed_admin_payload}")
    expect(isinstance(refreshed_admin_payload, dict), "enterprise admin refreshed payload invalid")
    updated_item = next(
        (item for item in refreshed_admin_payload.get("items") or [] if int(item.get("id") or 0) == request_id),
        None,
    )
    expect(updated_item is not None, "enterprise admin lost the updated request after status refresh")
    expect(
        str(updated_item.get("status") or "") == "in_progress",
        "enterprise request status update did not propagate to the enterprise admin feed",
    )


def assert_platform_bug_feedback_visibility() -> None:
    personal_token = login_token("personal_demo", "personal123")
    operator_token = login_token("enterprise_operator_demo", "operator123")
    platform_token = login_token("platform_admin_demo", "platform123")

    create_status, create_payload = request_json(
        "/feedback/platform-bugs",
        method="POST",
        token=personal_token,
        payload={
            "category": "logic",
            "title": "Smoke platform bug",
            "content": "Verify that platform admins can see newly submitted bug feedback.",
        },
    )
    expect(create_status == 200, f"platform bug feedback creation failed: {create_payload}")
    expect(isinstance(create_payload, dict), "platform bug creation payload invalid")
    created_item = create_payload.get("item") or {}
    feedback_id = int(created_item.get("id") or 0)
    expect(feedback_id > 0, "platform bug creation did not return a valid feedback id")

    personal_status, personal_payload = request_json("/feedback/platform-bugs", token=personal_token)
    expect(personal_status == 200, f"personal platform bug feed failed: {personal_payload}")
    expect(isinstance(personal_payload, dict), "personal platform bug payload invalid")
    expect(personal_payload.get("management") is False, "personal platform bug feed should not be in management mode")
    expect(
        any(int(item.get("id") or 0) == feedback_id for item in personal_payload.get("items") or []),
        "submitter could not see the newly created platform bug feedback",
    )

    operator_status, operator_payload = request_json("/feedback/platform-bugs", token=operator_token)
    expect(operator_status == 200, f"operator platform bug feed failed: {operator_payload}")
    expect(isinstance(operator_payload, dict), "operator platform bug payload invalid")
    expect(operator_payload.get("management") is False, "enterprise operator should not be in platform management mode")
    expect(
        all(int(item.get("id") or 0) != feedback_id for item in operator_payload.get("items") or []),
        "non-manager account should not see another user's platform bug feedback item",
    )

    platform_status, platform_payload = request_json("/feedback/platform-bugs", token=platform_token)
    expect(platform_status == 200, f"platform admin bug feed failed: {platform_payload}")
    expect(isinstance(platform_payload, dict), "platform admin bug payload invalid")
    expect(platform_payload.get("management") is True, "platform admin bug feed should be in management mode")
    expect(
        any(int(item.get("id") or 0) == feedback_id for item in platform_payload.get("items") or []),
        "platform admin could not see the newly created bug feedback",
    )
    expect(
        int((platform_payload.get("summary") or {}).get("open") or 0) >= 1,
        "platform admin summary did not reflect the new open bug feedback",
    )

    update_status, update_payload = request_json(
        f"/feedback/platform-bugs/{feedback_id}/status",
        method="POST",
        token=platform_token,
        payload={
            "status": "resolved",
            "response_note": "Platform admin resolved the smoke feedback.",
        },
    )
    expect(update_status == 200, f"platform bug status update failed: {update_payload}")

    refreshed_personal_status, refreshed_personal_payload = request_json("/feedback/platform-bugs", token=personal_token)
    expect(refreshed_personal_status == 200, f"personal refresh bug feed failed: {refreshed_personal_payload}")
    expect(isinstance(refreshed_personal_payload, dict), "personal refresh bug payload invalid")
    updated_item = next(
        (item for item in refreshed_personal_payload.get("items") or [] if int(item.get("id") or 0) == feedback_id),
        None,
    )
    expect(updated_item is not None, "submitter lost the updated bug feedback after refresh")
    expect(
        str(updated_item.get("status") or "") == "resolved",
        "platform bug status update did not propagate back to the submitter feed",
    )


def main() -> None:
    cleanup_db_file()
    process: subprocess.Popen[str] | None = None
    process_output = ""
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", HOST, "--port", str(PORT)],
            cwd=str(BACKEND_DIR),
            env=build_server_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        wait_for_server_ready(process)
        assert_enterprise_request_visibility()
        assert_platform_bug_feedback_visibility()
        print("FEEDBACK_NOTIFICATION_SMOKE_OK enterprise_request platform_bug_feedback")
    except Exception:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process is not None and process.stdout is not None:
            try:
                process_output = process.stdout.read()
            except Exception:
                process_output = ""
        raise RuntimeError(
            "feedback notification smoke failed"
            + (f"\n--- backend output ---\n{process_output}".rstrip() if process_output else "")
        )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        cleanup_db_file()


if __name__ == "__main__":
    main()
