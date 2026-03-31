from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Request

from app.core.auth_capabilities import build_capability_groups, get_role_capabilities, has_capability, normalize_role
from app.core.auth_security import hash_password, issue_session_token, utc_timestamp, verify_password
from app.core.settings import get_settings
from app.models.auth import AuthSession, AuthUser
from app.models.enterprise_application import EnterpriseApplication
from app.repositories.auth_repository import (
    list_users,
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
            "suspension_reason": None,
            "suspension_note": None,
            "suspended_at": None,
            "suspended_until": None,
            "suspended_by": None,
            "deactivated_at": None,
            "deactivated_by": None,
            "created_at": None,
            "last_login_at": None,
            "governance_updated_at": None,
        },
    }


def _public_user_payload(user) -> dict:
    user = _release_expired_suspension(user)
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
        "suspension_reason": getattr(user, "suspension_reason", None),
        "suspension_note": getattr(user, "suspension_note", None),
        "suspended_at": getattr(user, "suspended_at", None),
        "suspended_until": getattr(user, "suspended_until", None),
        "suspended_by": getattr(user, "suspended_by", None),
        "deactivated_at": getattr(user, "deactivated_at", None),
        "deactivated_by": getattr(user, "deactivated_by", None),
        "created_at": getattr(user, "created_at", None),
        "last_login_at": getattr(user, "last_login_at", None),
        "governance_updated_at": getattr(user, "governance_updated_at", None),
        "enterprise_application": _serialize_enterprise_application(enterprise_application) if enterprise_application else None,
        "capabilities": capabilities,
        "capability_groups": build_capability_groups(normalized_role, account_status=account_status),
    }


def _serialize_managed_user(user) -> dict:
    payload = _public_user_payload(user)
    return {
        "id": payload["id"],
        "username": payload["username"],
        "display_name": payload["display_name"],
        "role": payload["role"],
        "active": payload["active"],
        "builtin": payload["builtin"],
        "account_status": payload["account_status"],
        "organization_id": payload["organization_id"],
        "organization_name": payload["organization_name"],
        "suspension_reason": payload["suspension_reason"],
        "suspension_note": payload["suspension_note"],
        "suspended_at": payload["suspended_at"],
        "suspended_until": payload["suspended_until"],
        "suspended_by": payload["suspended_by"],
        "deactivated_at": payload["deactivated_at"],
        "deactivated_by": payload["deactivated_by"],
        "created_at": payload["created_at"],
        "last_login_at": payload["last_login_at"],
        "governance_updated_at": payload["governance_updated_at"],
        "enterprise_application": payload["enterprise_application"],
    }


def _parse_iso_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _release_expired_suspension(user):
    if user is None:
        return None
    if str(getattr(user, "account_status", "approved") or "approved").lower() != "suspended":
        return user
    suspended_until = _parse_iso_datetime(getattr(user, "suspended_until", None))
    if suspended_until is None or suspended_until > datetime.now():
        return user
    user.account_status = "approved"
    user.suspension_reason = None
    user.suspension_note = None
    user.suspended_at = None
    user.suspended_until = None
    user.suspended_by = None
    user.governance_updated_at = now_iso()
    return upsert_user(user)


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


def _raise_if_login_restricted(user) -> None:
    user = _release_expired_suspension(user)
    account_status = str(getattr(user, "account_status", "approved") or "approved")
    if account_status == "suspended":
        raise_api_error(
            403,
            "auth_account_suspended",
            reason=getattr(user, "suspension_reason", None),
            note=getattr(user, "suspension_note", None),
            suspended_until=getattr(user, "suspended_until", None),
        )
    if account_status == "deactivated" or not bool(getattr(user, "active", True)):
        raise_api_error(
            403,
            "auth_account_deactivated",
            note=getattr(user, "suspension_note", None),
        )


def _resolve_governance_actor_and_target(request: Request, user_id: str):
    actor = require_actor_capability(request, "system.manage")
    target = get_user_by_id(str(user_id or "").strip())
    if target is None:
        raise_api_error(404, "auth_user_not_found")
    target = _release_expired_suspension(target)
    if str(actor.get("id") or "") == str(target.id or ""):
        raise_api_error(403, "auth_governance_self_locked")
    if normalize_role(target.role) == "platform_admin":
        raise_api_error(403, "auth_governance_platform_admin_protected")
    return actor, target


def suspend_user_account(
    request: Request,
    user_id: str,
    reason: str,
    note: str | None = None,
    duration_days: int | None = None,
    permanent: bool = False,
) -> dict:
    actor, target = _resolve_governance_actor_and_target(request, user_id)
    normalized_reason = str(reason or "").strip()
    if not normalized_reason:
        raise_api_error(400, "auth_governance_suspend_reason_required")
    if str(getattr(target, "account_status", "approved") or "approved").lower() == "deactivated":
        raise_api_error(400, "auth_governance_already_deactivated")

    normalized_duration = None if permanent else max(int(duration_days or 0), 0)
    if not permanent and normalized_duration <= 0:
        raise_api_error(400, "auth_governance_duration_invalid")

    suspended_at = now_iso()
    suspended_until = None if permanent else (datetime.now() + timedelta(days=normalized_duration)).isoformat(timespec="seconds")
    target.account_status = "suspended"
    target.suspension_reason = normalized_reason
    target.suspension_note = str(note or "").strip() or None
    target.suspended_at = suspended_at
    target.suspended_until = suspended_until
    target.suspended_by = str(actor.get("username") or actor.get("id") or "platform_admin")
    target.governance_updated_at = suspended_at
    updated = upsert_user(target)
    remove_sessions_for_user(updated.id)
    record_operation_audit(
        "user_account",
        updated.id,
        "user.suspend",
        actor=actor,
        metadata={
            "target_username": updated.username,
            "target_role": updated.role,
            "reason": updated.suspension_reason,
            "note": updated.suspension_note,
            "permanent": bool(permanent),
            "duration_days": None if permanent else normalized_duration,
            "suspended_until": updated.suspended_until,
        },
    )
    return {"item": _serialize_managed_user(updated)}


def unsuspend_user_account(request: Request, user_id: str) -> dict:
    actor, target = _resolve_governance_actor_and_target(request, user_id)
    if str(getattr(target, "account_status", "approved") or "approved").lower() != "suspended":
        raise_api_error(400, "auth_governance_not_suspended")
    target.account_status = "approved"
    target.suspension_reason = None
    target.suspension_note = None
    target.suspended_at = None
    target.suspended_until = None
    target.suspended_by = None
    target.governance_updated_at = now_iso()
    updated = upsert_user(target)
    record_operation_audit(
        "user_account",
        updated.id,
        "user.unsuspend",
        actor=actor,
        metadata={
            "target_username": updated.username,
            "target_role": updated.role,
        },
    )
    return {"item": _serialize_managed_user(updated)}


def deactivate_user_account(
    request: Request,
    user_id: str,
    reason: str | None = None,
    note: str | None = None,
) -> dict:
    actor, target = _resolve_governance_actor_and_target(request, user_id)
    if str(getattr(target, "account_status", "approved") or "approved").lower() == "deactivated":
        raise_api_error(400, "auth_governance_already_deactivated")
    normalized_reason = str(reason or "").strip()
    target.active = False
    target.account_status = "deactivated"
    target.deactivated_at = now_iso()
    target.deactivated_by = str(actor.get("username") or actor.get("id") or "platform_admin")
    target.suspension_note = str(note or "").strip() or target.suspension_note
    target.suspension_reason = normalized_reason or target.suspension_reason or "deactivated"
    target.suspended_at = None
    target.suspended_until = None
    target.suspended_by = None
    target.governance_updated_at = target.deactivated_at
    updated = upsert_user(target)
    remove_sessions_for_user(updated.id)
    record_operation_audit(
        "user_account",
        updated.id,
        "user.deactivate",
        actor=actor,
        metadata={
            "target_username": updated.username,
            "target_role": updated.role,
            "reason": updated.suspension_reason,
            "note": updated.suspension_note,
        },
    )
    return {"item": _serialize_managed_user(updated)}


def login(username: str, password: str) -> dict:
    normalized_username = str(username or "").strip()
    normalized_password = str(password or "")
    if not normalized_username or not normalized_password:
        raise_api_error(400, "auth_credentials_required")

    user = get_user_by_username(normalized_username)
    if user is None or not user.active or not verify_password(normalized_password, user.password_hash):
        raise_api_error(401, "auth_invalid_credentials")
    _raise_if_login_restricted(user)

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
    user.last_login_at = now_iso()
    upsert_session(session)
    upsert_user(user)
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
        created_at=now_iso(),
        governance_updated_at=now_iso(),
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


def register_personal(
    username: str,
    password: str,
    display_name: str | None = None,
) -> dict:
    normalized_username = str(username or "").strip()
    normalized_password = str(password or "")
    normalized_display_name = str(display_name or "").strip()

    if not normalized_username or not normalized_password:
        raise_api_error(400, "personal_register_fields_required")
    if len(normalized_username) < 4:
        raise_api_error(400, "personal_register_username_invalid")
    if len(normalized_password) < 8:
        raise_api_error(400, "personal_register_password_invalid")
    if get_user_by_username(normalized_username) is not None:
        raise_api_error(409, "personal_register_username_taken")
    if get_enterprise_application_by_username(normalized_username) is not None:
        raise_api_error(409, "personal_register_username_taken")

    timestamp = now_iso()
    user = AuthUser(
        id=normalized_username,
        username=normalized_username,
        display_name=normalized_display_name or normalized_username,
        role="personal",
        password_hash=hash_password(normalized_password),
        active=True,
        builtin=False,
        account_status="approved",
        organization_id=None,
        organization_name=None,
        created_at=timestamp,
        governance_updated_at=timestamp,
        last_login_at=timestamp,
    )
    upsert_user(user)
    record_operation_audit(
        "user_account",
        user.id,
        "user.register.personal",
        actor={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "account_status": user.account_status,
            "authenticated": False,
        },
        metadata={
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "builtin": user.builtin,
        },
    )

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


def _filter_user_feed(
    role: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list, dict, str, str, str]:
    normalized_role = str(role or "").strip().lower()
    normalized_status = str(status or "").strip().lower()
    normalized_search = str(search or "").strip().casefold()

    users = [_release_expired_suspension(user) for user in list_users()]

    def matches_role(user) -> bool:
        if not normalized_role or normalized_role == "all":
            return True
        user_role = normalize_role(getattr(user, "role", "guest"))
        if normalized_role == "enterprise":
            return user_role.startswith("enterprise_")
        return user_role == normalized_role

    def matches_status(user) -> bool:
        if not normalized_status or normalized_status == "all":
            return True
        return str(getattr(user, "account_status", "approved") or "approved").lower() == normalized_status

    def matches_search(user) -> bool:
        if not normalized_search:
            return True
        haystack = " ".join(
            [
                str(getattr(user, "username", "") or ""),
                str(getattr(user, "display_name", "") or ""),
                str(getattr(user, "organization_name", "") or ""),
            ]
        ).casefold()
        return normalized_search in haystack

    filtered_items = [
        user for user in users
        if matches_role(user) and matches_status(user) and matches_search(user)
    ]
    filtered_items.sort(
        key=lambda user: (
            str(getattr(user, "created_at", "") or ""),
            str(getattr(user, "username", "") or ""),
        ),
        reverse=True,
    )
    summary = {
        "all": len(users),
        "personal": sum(1 for user in users if normalize_role(getattr(user, "role", "guest")) == "personal"),
        "enterprise": sum(1 for user in users if normalize_role(getattr(user, "role", "guest")).startswith("enterprise_")),
        "platform_admin": sum(1 for user in users if normalize_role(getattr(user, "role", "guest")) == "platform_admin"),
        "approved": sum(1 for user in users if str(getattr(user, "account_status", "approved") or "approved") == "approved"),
        "pending": sum(1 for user in users if str(getattr(user, "account_status", "approved") or "approved") == "pending"),
        "rejected": sum(1 for user in users if str(getattr(user, "account_status", "approved") or "approved") == "rejected"),
        "suspended": sum(1 for user in users if str(getattr(user, "account_status", "approved") or "approved") == "suspended"),
        "deactivated": sum(1 for user in users if str(getattr(user, "account_status", "approved") or "approved") == "deactivated"),
    }
    return filtered_items, summary, normalized_role or "all", normalized_status or "all", str(search or "").strip()


def list_user_feed(
    role: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 60,
) -> dict:
    safe_limit = max(1, min(int(limit or 60), 200))
    filtered_items, summary, normalized_role, normalized_status, normalized_search = _filter_user_feed(
        role=role,
        status=status,
        search=search,
    )
    return {
        "items": [_serialize_managed_user(user) for user in filtered_items[:safe_limit]],
        "summary": summary,
        "role": normalized_role,
        "status": normalized_status,
        "search": normalized_search,
        "limit": safe_limit,
    }


def export_user_feed(request: Request, role: str | None = None, status: str | None = None, search: str | None = None) -> dict:
    actor = require_actor_capability(request, "system.manage")
    filtered_items, summary, normalized_role, normalized_status, normalized_search = _filter_user_feed(
        role=role,
        status=status,
        search=search,
    )
    items = [_serialize_managed_user(user) for user in filtered_items]
    record_operation_audit(
        "user_account",
        str(actor.get("id") or actor.get("username") or "platform_admin"),
        "user.export",
        actor=actor,
        metadata={
            "role_filter": normalized_role,
            "status_filter": normalized_status,
            "search": normalized_search,
            "count": len(items),
        },
    )
    return {
        "items": items,
        "summary": summary,
        "role": normalized_role,
        "status": normalized_status,
        "search": normalized_search,
        "exported_at": now_iso(),
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
