from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type


LEGACY_AUTH_PASSWORD_SALT = b"agv-dispatch-demo-auth"
PASSWORD_HASHER = PasswordHasher(type=Type.ID)


def _legacy_hash_password(password: str) -> str:
    normalized = str(password or "").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", normalized, LEGACY_AUTH_PASSWORD_SALT, 120_000).hex()


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(str(password or ""))


def verify_password(password: str, password_hash: str) -> bool:
    encoded = str(password_hash or "")
    if encoded.startswith("$argon2"):
        try:
            return bool(PASSWORD_HASHER.verify(encoded, str(password or "")))
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False
    return hmac.compare_digest(_legacy_hash_password(password), encoded)


def password_needs_rehash(password_hash: str) -> bool:
    encoded = str(password_hash or "")
    if not encoded.startswith("$argon2"):
        return True
    try:
        return PASSWORD_HASHER.check_needs_rehash(encoded)
    except InvalidHashError:
        return True


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def utc_timestamp() -> int:
    return int(time.time())
