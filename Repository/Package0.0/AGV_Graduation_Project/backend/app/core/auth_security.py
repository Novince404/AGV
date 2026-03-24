from __future__ import annotations

import hashlib
import secrets
import time


AUTH_PASSWORD_SALT = b"agv-dispatch-demo-auth"


def hash_password(password: str) -> str:
    normalized = str(password or "").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", normalized, AUTH_PASSWORD_SALT, 120_000).hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == str(password_hash or "")


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def utc_timestamp() -> int:
    return int(time.time())
