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
SMOKE_DB_PATH = BACKEND_DIR / "agv_enterprise_client_smoke.db"
HOST = "127.0.0.1"
PORT = 8011
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
        raise RuntimeError(f"enterprise client smoke backend exited early.\n{output}".strip())
    raise RuntimeError(f"enterprise client smoke backend did not become ready in time: {last_error}")


def assert_enterprise_role_login_chain(
    *,
    label: str,
    username: str,
    password: str,
    expected_role: str,
    expected_capability_groups: dict[str, bool],
) -> None:
    login_status, login_payload = request_json(
        "/auth/login",
        method="POST",
        payload={
            "username": username,
            "password": password,
        },
    )
    expect(login_status == 200, f"{label} login failed: {login_payload}")
    expect(isinstance(login_payload, dict) and bool(login_payload.get("authenticated")), f"{label} login payload invalid")
    session_token = str(login_payload.get("session_token") or "").strip()
    expect(bool(session_token), f"{label} missing session token")

    me_status, me_payload = request_json("/auth/me", token=session_token)
    expect(me_status == 200, f"{label} auth/me failed: {me_payload}")
    expect(isinstance(me_payload, dict) and bool(me_payload.get("authenticated")), f"{label} auth/me invalid")
    expect(str(me_payload.get("user", {}).get("role") or "") == expected_role, f"{label} role mismatch")
    expect(
        str(me_payload.get("user", {}).get("organization_id") or "") == "org_demo_enterprise",
        f"{label} organization mismatch",
    )
    capability_groups = me_payload.get("capability_groups") or {}
    for group_key, expected_value in expected_capability_groups.items():
        expect(
            bool(capability_groups.get(group_key)) is expected_value,
            f"{label} capability group {group_key} mismatch",
        )

    map_status, map_payload = request_json("/status/map", token=session_token)
    expect(map_status == 200, f"{label} map load failed: {map_payload}")
    expect(isinstance(map_payload, dict), f"{label} map payload invalid")
    expect(isinstance(map_payload.get("blocked_cells"), list), f"{label} map blocked_cells missing")
    expect(isinstance(map_payload.get("topology"), dict), f"{label} map topology missing")

    agv_status, agv_payload = request_json("/agv/list", token=session_token)
    expect(agv_status == 200, f"{label} agv list failed: {agv_payload}")
    expect(isinstance(agv_payload, list), f"{label} agv payload invalid")

    task_status, task_payload = request_json("/task/list", token=session_token)
    expect(task_status == 200, f"{label} task list failed: {task_payload}")
    expect(isinstance(task_payload, list), f"{label} task payload invalid")

    settings_status, settings_payload = request_json("/status/ui-settings", token=session_token)
    expect(settings_status == 200, f"{label} ui settings failed: {settings_payload}")
    expect(isinstance(settings_payload, dict), f"{label} ui settings payload invalid")
    expect("low_battery_threshold" in settings_payload, f"{label} ui settings missing low_battery_threshold")
    expect(
        "idle_charge_battery_threshold" in settings_payload,
        f"{label} ui settings missing idle_charge_battery_threshold",
    )

    members_status, members_payload = request_json("/auth/enterprise-members", token=session_token)
    if expected_role == "enterprise_admin":
        expect(members_status == 200, f"{label} enterprise members failed: {members_payload}")
        expect(isinstance(members_payload, dict), f"{label} enterprise members payload invalid")
        usernames = {str(item.get("username") or "") for item in members_payload.get("items") or []}
        expect("enterprise_demo" in usernames, f"{label} members missing enterprise_demo")
        expect("enterprise_operator_demo" in usernames, f"{label} members missing enterprise_operator_demo")
        expect("enterprise_logistics_demo" in usernames, f"{label} members missing enterprise_logistics_demo")
    else:
        expect(members_status == 403, f"{label} should not access enterprise members, got {members_status}")

    logout_status, logout_payload = request_json("/auth/logout", method="POST", token=session_token)
    expect(logout_status == 200, f"{label} logout failed: {logout_payload}")
    guest_status, guest_payload = request_json("/auth/me", token=session_token)
    expect(guest_status == 200, f"{label} post-logout auth/me failed: {guest_payload}")
    expect(isinstance(guest_payload, dict) and not bool(guest_payload.get("authenticated")), f"{label} logout did not clear session")


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

        guest_status, guest_payload = request_json("/auth/me")
        expect(guest_status == 200, f"guest auth/me failed: {guest_payload}")
        expect(isinstance(guest_payload, dict) and not bool(guest_payload.get("authenticated")), "guest should not be authenticated")

        assert_enterprise_role_login_chain(
            label="enterprise_admin",
            username="enterprise_demo",
            password="enterprise123",
            expected_role="enterprise_admin",
            expected_capability_groups={
                "dispatch": True,
                "fault": True,
                "map": True,
                "data": True,
                "audit": True,
                "ai": True,
                "platform": False,
            },
        )
        assert_enterprise_role_login_chain(
            label="enterprise_operator",
            username="enterprise_operator_demo",
            password="operator123",
            expected_role="enterprise_operator",
            expected_capability_groups={
                "dispatch": True,
                "fault": True,
                "map": False,
                "data": False,
                "audit": False,
                "ai": True,
                "platform": False,
            },
        )
        assert_enterprise_role_login_chain(
            label="enterprise_logistics",
            username="enterprise_logistics_demo",
            password="logistics123",
            expected_role="enterprise_logistics",
            expected_capability_groups={
                "dispatch": False,
                "fault": False,
                "map": True,
                "data": True,
                "audit": False,
                "ai": True,
                "platform": False,
            },
        )

        print("ENTERPRISE_CLIENT_LOGIN_SMOKE_OK enterprise_admin enterprise_operator enterprise_logistics")
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
            "enterprise client login smoke failed"
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
