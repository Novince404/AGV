from __future__ import annotations

from fastapi import Request

from app.core.auth_capabilities import build_capability_groups, get_role_capabilities, has_capability, normalize_role
from app.core.auth_security import hash_password, issue_session_token, utc_timestamp, verify_password
from app.core.settings import get_settings
from app.models.auth import AuthSession, AuthUser
from app.models.enterprise_application import EnterpriseApplication
from app.repositories.auth_repository import (
    get_session_by_token,
    get_user_by_id,
    get_user_by_username,
    remove_session,
    remove_sessions_for_user,
    upsert_session,
    upsert_user,
)
from app.repositories.enterprise_application_repository import (
    get_enterprise_application_by_id,
    get_enterprise_application_by_user_id,
    get_enterprise_application_by_username,
    get_next_enterprise_application_id,
    list_enterprise_applications,
    upsert_enterprise_application,
)
from app.services.operation_audit_service import list_recent_operation_audits
from app.services.operation_audit_service import now_iso, record_operation_audit, remove_operation_audit_entry
from app.utils.api_error import raise_api_error


def _guest_payload() -> dict:
    capabilities = sorted(get_role_capabilities("guest", account_status="approved"))
    return {
        "authenticated": False,
        "session_expires_at": None,
        "capabilities": capabilities,
        "capability_groups": build_capability_groups("guest", account_status="approved"),
        "user": {
            "id": "guest",
            "username": "guest",
            "display_name": "Guest",
            "role": "guest",
            "active": True,
            "builtin": True,
            "account_status": "guest",
            "organization_id": None,
            "organization_name": None,
        },
    }


def _public_user_payload(user) -> dict:
    normalized_role = normalize_role(user.role)
    account_status = str(getattr(user, "account_status", "approved") or "approved")
    capabilities = sorted(get_role_capabilities(normalized_role, account_status=account_status))
    enterprise_application = get_enterprise_application_by_user_id(str(getattr(user, "id", "") or ""))
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": normalized_role,
        "active": bool(user.active),
        "builtin": bool(user.builtin),
        "account_status": account_status,
        "organization_id": getattr(user, "organization_id", None),
        "organization_name": getattr(user, "organization_name", None),
        "enterprise_application": _serialize_enterprise_application(enterprise_application) if enterprise_application else None,
        "capabilities": capabilities,
        "capability_groups": build_capability_groups(normalized_role, account_status=account_status),
    }


def _build_authenticated_payload(user, session: AuthSession) -> dict:
    user_payload = _public_user_payload(user)
    return {
        "authenticated": True,
        "session_token": session.token,
        "session_expires_at": int(session.expires_at),
        "capabilities": user_payload["capabilities"],
        "capability_groups": user_payload["capability_groups"],
        "user": user_payload,
    }


def resolve_request_actor(request: Request) -> dict:
    resolved = _resolve_current_session(request, touch=True)
    if resolved is None:
        guest = _guest_payload()["user"]
        return {
            **guest,
            "authenticated": False,
            "capabilities": sorted(get_role_capabilities("guest", account_status="approved")),
            "capability_groups": build_capability_groups("guest", account_status="approved"),
        }

    user, _session = resolved
    return {
        **_public_user_payload(user),
        "authenticated": True,
    }


def require_authenticated_actor(request: Request, allowed_roles: set[str] | None = None) -> dict:
    actor = resolve_request_actor(request)
    if not actor.get("authenticated"):
        raise_api_error(401, "auth_login_required")

    if allowed_roles and actor.get("role") not in allowed_roles:
        raise_api_error(403, "auth_permission_denied")
    return actor


def require_actor_capability(request: Request, capability: str, allowed_roles: set[str] | None = None) -> dict:
    actor = require_authenticated_actor(request, allowed_roles=allowed_roles)
    if not has_capability(actor.get("role"), capability, account_status=actor.get("account_status")):
        raise_api_error(403, "auth_permission_denied")
    return actor


def _extract_session_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return token
    return request.cookies.get("agv_session")


def _resolve_current_session(request: Request, touch: bool = True) -> tuple[object, AuthSession] | None:
    token = _extract_session_token(request)
    if not token:
        return None

    session = get_session_by_token(token)
    if session is None:
        return None

    now = utc_timestamp()
    if int(session.expires_at) <= now:
        remove_session(token)
        return None

    user = get_user_by_id(session.user_id)
    if user is None or not user.active:
        remove_session(token)
        return None

    if touch:
        session.last_seen_at = now
        upsert_session(session)

    return user, session


def login(username: str, password: str) -> dict:
    normalized_username = str(username or "").strip()
    normalized_password = str(password or "")
    if not normalized_username or not normalized_password:
        raise_api_error(400, "auth_credentials_required")

    user = get_user_by_username(normalized_username)
    if user is None or not user.active or not verify_password(normalized_password, user.password_hash):
        raise_api_error(401, "auth_invalid_credentials")

    remove_sessions_for_user(user.id)
    now = utc_timestamp()
    ttl = max(int(get_settings().auth_session_ttl_sec), 300)
    session = AuthSession(
        token=issue_session_token(),
        user_id=user.id,
        created_at=now,
        expires_at=now + ttl,
        last_seen_at=now,
    )
    upsert_session(session)
    return _build_authenticated_payload(user, session)


def logout(request: Request) -> dict:
    token = _extract_session_token(request)
    if token:
        remove_session(token)
    return _guest_payload()


def get_current_auth(request: Request) -> dict:
    resolved = _resolve_current_session(request, touch=True)
    if resolved is None:
        return _guest_payload()
    user, session = resolved
    return _build_authenticated_payload(user, session)


def _serialize_enterprise_application(application: EnterpriseApplication) -> dict:
    return {
        "id": int(application.id),
        "company_name": application.company_name,
        "contact_name": application.contact_name,
        "contact_email": application.contact_email,
        "username": application.username,
        "user_id": application.user_id,
        "status": application.status,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "reviewed_by": application.reviewed_by,
        "review_note": application.review_note,
        "organization_id": application.organization_id,
    }


def register_enterprise(
    company_name: str,
    contact_name: str,
    contact_email: str,
    username: str,
    password: str,
) -> dict:
    normalized_company_name = str(company_name or "").strip()
    normalized_contact_name = str(contact_name or "").strip()
    normalized_contact_email = str(contact_email or "").strip()
    normalized_username = str(username or "").strip()
    normalized_password = str(password or "")

    if not all(
        [
            normalized_company_name,
            normalized_contact_name,
            normalized_contact_email,
            normalized_username,
            normalized_password,
        ]
    ):
        raise_api_error(400, "enterprise_application_fields_required")

    if get_user_by_username(normalized_username) is not None:
        raise_api_error(409, "enterprise_application_username_taken")
    if get_enterprise_application_by_username(normalized_username) is not None:
        raise_api_error(409, "enterprise_application_username_taken")

    user = AuthUser(
        id=normalized_username,
        username=normalized_username,
        display_name=normalized_contact_name,
        role="enterprise_admin",
        password_hash=hash_password(normalized_password),
        active=True,
        builtin=False,
        account_status="pending",
        organization_id=None,
        organization_name=normalized_company_name,
    )
    upsert_user(user)

    application = EnterpriseApplication(
        id=get_next_enterprise_application_id(),
        company_name=normalized_company_name,
        contact_name=normalized_contact_name,
        contact_email=normalized_contact_email,
        username=normalized_username,
        user_id=user.id,
        status="pending",
        submitted_at=now_iso(),
        reviewed_at=None,
        reviewed_by=None,
        review_note=None,
        organization_id=None,
    )
    upsert_enterprise_application(application)
    record_operation_audit(
        "enterprise_application",
        application.id,
        "create",
        actor={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "account_status": user.account_status,
            "authenticated": False,
        },
        metadata={
            "company_name": application.company_name,
            "username": application.username,
            "status": application.status,
        },
    )
    return {
        "message": "enterprise_application_submitted",
        "application": _serialize_enterprise_application(application),
    }


def list_enterprise_application_feed(status: str | None = None) -> dict:
    normalized_status = str(status or "").strip().lower()
    items = list_enterprise_applications()
    if normalized_status and normalized_status != "all":
        items = [item for item in items if item.status.lower() == normalized_status]
    items = sorted(items, key=lambda item: (item.submitted_at, int(item.id)), reverse=True)
    summary = {
        "all": len(list_enterprise_applications()),
        "pending": sum(1 for item in list_enterprise_applications() if item.status == "pending"),
        "approved": sum(1 for item in list_enterprise_applications() if item.status == "approved"),
        "rejected": sum(1 for item in list_enterprise_applications() if item.status == "rejected"),
    }
    return {
        "items": [_serialize_enterprise_application(item) for item in items],
        "summary": summary,
        "status": normalized_status or "all",
    }


def get_enterprise_application_detail(application_id: int) -> dict:
    application = get_enterprise_application_by_id(int(application_id or 0))
    if application is None:
        raise_api_error(404, "enterprise_application_not_found")
    user = get_user_by_id(application.user_id)
    return {
        "application": _serialize_enterprise_application(application),
        "user": _public_user_payload(user) if user is not None else None,
    }


def review_enterprise_application(
    request: Request,
    application_id: int,
    decision: str,
    review_note: str | None = None,
) -> dict:
    actor = require_actor_capability(request, "enterprise.approve")
    application = get_enterprise_application_by_id(int(application_id or 0))
    if application is None:
        raise_api_error(404, "enterprise_application_not_found")
    if application.status != "pending":
        raise_api_error(409, "enterprise_application_already_reviewed")

    decision_normalized = str(decision or "").strip().lower()
    if decision_normalized not in {"approve", "reject"}:
        raise_api_error(400, "enterprise_application_invalid_decision")

    user = get_user_by_id(application.user_id)
    if user is None:
        raise_api_error(404, "auth_user_not_found")

    trimmed_note = str(review_note or "").strip() or None
    if decision_normalized == "approve":
        organization_id = application.organization_id or f"org_{application.id}"
        user.role = "enterprise_admin"
        user.account_status = "approved"
        user.organization_id = organization_id
        user.organization_name = application.company_name
        application.status = "approved"
        application.organization_id = organization_id
    else:
        user.role = normalize_role(user.role)
        user.account_status = "rejected"
        user.organization_id = None
        user.organization_name = application.company_name
        application.status = "rejected"

    application.reviewed_at = now_iso()
    application.reviewed_by = str(actor.get("username") or actor.get("display_name") or "platform_admin")
    application.review_note = trimmed_note

    upsert_user(user)
    upsert_enterprise_application(application)
    record_operation_audit(
        "enterprise_application",
        application.id,
        "approve" if decision_normalized == "approve" else "reject",
        actor=actor,
        metadata={
            "company_name": application.company_name,
            "username": application.username,
            "status": application.status,
            "review_note": trimmed_note,
        },
    )
    return {
        "message": f"enterprise_application_{application.status}",
        "application": _serialize_enterprise_application(application),
        "user": _public_user_payload(user),
    }


def list_operation_feed(limit: int = 60, resource_type: str | None = None, action: str | None = None) -> dict:
    return {
        "items": list_recent_operation_audits(limit=limit, resource_type=resource_type, action=action),
        "limit": max(1, min(int(limit or 60), 200)),
        "resource_type": str(resource_type or "").strip().lower() or None,
        "action": str(action or "").strip().lower() or None,
    }


def delete_operation_feed_item(request: Request, audit_id: int) -> dict:
    require_actor_capability(request, "audit.view")
    return {
        "item": remove_operation_audit_entry(audit_id),
    }
