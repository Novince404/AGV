from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "dist" / "AGV_Enterprise_Client_v1"
BACKEND_EXE = PACKAGE_DIR / "backend.exe"
HOST = "127.0.0.1"
PORT = 8012
BASE_URL = f"http://{HOST}:{PORT}"


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_server_env() -> dict[str, str]:
    env = os.environ.copy()
    env["AGV_HOST"] = HOST
    env["AGV_PORT"] = str(PORT)
    env["AGV_SERVE_FRONTEND_DIST"] = "true"
    env["AGV_DATABASE_AUTO_CREATE"] = "true"
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


def request_status(path: str) -> int:
    req = request.Request(f"{BASE_URL}{path}", method="GET")
    try:
        with request.urlopen(req, timeout=4) as response:
            response.read()
            return int(response.status)
    except error.HTTPError as exc:
        return int(exc.code)


def wait_for_server_ready(process: subprocess.Popen[str]) -> None:
    last_error: Exception | None = None
    for _ in range(50):
        if process.poll() is not None:
            break
        try:
            root_status = request_status("/")
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
        raise RuntimeError(f"packaged enterprise backend exited early.\n{output}".strip())
    raise RuntimeError(f"packaged enterprise backend did not become ready in time: {last_error}")


def assert_packaged_role_login_chain(
    *,
    label: str,
    username: str,
    password: str,
    expected_role: str,
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

    map_status, map_payload = request_json("/status/map", token=session_token)
    expect(map_status == 200, f"{label} map load failed: {map_payload}")
    expect(isinstance(map_payload, dict) and isinstance(map_payload.get("topology"), dict), f"{label} map topology missing")

    agv_status, agv_payload = request_json("/agv/list", token=session_token)
    expect(agv_status == 200 and isinstance(agv_payload, list), f"{label} agv list failed: {agv_payload}")

    task_status, task_payload = request_json("/task/list", token=session_token)
    expect(task_status == 200 and isinstance(task_payload, list), f"{label} task list failed: {task_payload}")

    settings_status, settings_payload = request_json("/status/ui-settings", token=session_token)
    expect(settings_status == 200 and isinstance(settings_payload, dict), f"{label} ui settings failed: {settings_payload}")
    expect("low_battery_threshold" in settings_payload, f"{label} ui settings missing low_battery_threshold")
    expect(
        "idle_charge_battery_threshold" in settings_payload,
        f"{label} ui settings missing idle_charge_battery_threshold",
    )

    logout_status, logout_payload = request_json("/auth/logout", method="POST", token=session_token)
    expect(logout_status == 200, f"{label} logout failed: {logout_payload}")


def main() -> None:
    expect(BACKEND_EXE.exists(), f"packaged backend.exe not found: {BACKEND_EXE}")
    process: subprocess.Popen[str] | None = None
    process_output = ""
    try:
        process = subprocess.Popen(
            [str(BACKEND_EXE)],
            cwd=str(PACKAGE_DIR),
            env=build_server_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        wait_for_server_ready(process)

        assert_packaged_role_login_chain(
            label="enterprise_admin",
            username="enterprise_demo",
            password="enterprise123",
            expected_role="enterprise_admin",
        )
        assert_packaged_role_login_chain(
            label="enterprise_operator",
            username="enterprise_operator_demo",
            password="operator123",
            expected_role="enterprise_operator",
        )
        assert_packaged_role_login_chain(
            label="enterprise_logistics",
            username="enterprise_logistics_demo",
            password="logistics123",
            expected_role="enterprise_logistics",
        )

        print("PACKAGED_ENTERPRISE_BACKEND_SMOKE_OK enterprise_admin enterprise_operator enterprise_logistics")
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
            "packaged enterprise backend smoke failed"
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


if __name__ == "__main__":
    main()
