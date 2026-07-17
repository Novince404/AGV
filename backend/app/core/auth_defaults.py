from __future__ import annotations

from app.core.auth_security import hash_password
from app.core.settings import get_settings
from app.models.auth import AuthUser


DEFAULT_AUTH_USERS = [
    {
        "id": "personal_demo",
        "username": "personal_demo",
        "display_name": "Personal Demo",
        "role": "personal",
        "password_hash": hash_password("personal123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": None,
        "organization_name": None,
    },
    {
        "id": "enterprise_demo",
        "username": "enterprise_demo",
        "display_name": "Enterprise Admin Demo",
        "role": "enterprise_admin",
        "password_hash": hash_password("enterprise123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": "org_demo_enterprise",
        "organization_name": "Enterprise Demo Co.",
    },
    {
        "id": "enterprise_operator_demo",
        "username": "enterprise_operator_demo",
        "display_name": "Enterprise Operator Demo",
        "role": "enterprise_operator",
        "password_hash": hash_password("operator123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": "org_demo_enterprise",
        "organization_name": "Enterprise Demo Co.",
    },
    {
        "id": "enterprise_logistics_demo",
        "username": "enterprise_logistics_demo",
        "display_name": "Enterprise Logistics Demo",
        "role": "enterprise_logistics",
        "password_hash": hash_password("logistics123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": "org_demo_enterprise",
        "organization_name": "Enterprise Demo Co.",
    },
    {
        "id": "admin_demo",
        "username": "admin_demo",
        "display_name": "Platform Admin Demo",
        "role": "platform_admin",
        "password_hash": hash_password("admin123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": None,
        "organization_name": None,
    },
    {
        "id": "platform_admin_demo",
        "username": "platform_admin_demo",
        "display_name": "Platform Admin Demo",
        "role": "platform_admin",
        "password_hash": hash_password("platform123"),
        "active": True,
        "builtin": True,
        "account_status": "approved",
        "organization_id": None,
        "organization_name": None,
    },
]


def build_default_auth_users() -> list[AuthUser]:
    settings = get_settings()
    users = [AuthUser(**item) for item in DEFAULT_AUTH_USERS] if settings.auth_demo_users_enabled else []
    if settings.bootstrap_admin_username and settings.bootstrap_admin_password:
        if len(settings.bootstrap_admin_password) < 12:
            raise RuntimeError("AGV_BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters")
        users.append(
            AuthUser(
                id="bootstrap_platform_admin",
                username=settings.bootstrap_admin_username,
                display_name="Platform Recovery Admin",
                role="platform_admin",
                password_hash=hash_password(settings.bootstrap_admin_password),
                active=True,
                builtin=True,
                account_status="approved",
            )
        )
    return users
