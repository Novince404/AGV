from __future__ import annotations

from app.core.auth_capabilities import normalize_role
from app.models.enterprise_request import EnterpriseRequest
from app.models.platform_bug_feedback import PlatformBugFeedback
from app.repositories.auth_repository import list_users
from app.repositories.enterprise_request_repository import (
    get_enterprise_request_by_id,
    get_next_enterprise_request_id,
    list_enterprise_requests,
    upsert_enterprise_request,
)
from app.repositories.platform_bug_feedback_repository import (
    get_next_platform_bug_feedback_id,
    get_platform_bug_feedback_by_id,
    list_platform_bug_feedback,
    upsert_platform_bug_feedback,
)
from app.services import auth_service
from app.services.operation_audit_service import now_iso, record_operation_audit
from app.utils.api_error import raise_api_error


ENTERPRISE_REQUEST_CATEGORIES = {"request", "error"}
PLATFORM_BUG_FEEDBACK_CATEGORIES = {"ui", "logic", "data", "permission", "other"}
FEEDBACK_STATUS_VALUES = {"open", "in_progress", "resolved", "closed"}


def _normalize_category(value: str | None) -> str:
    return str(value or "").strip().lower()


def _normalize_status(value: str | None) -> str:
    return str(value or "").strip().lower()


def _match_search(fields: list[str | None], keyword: str) -> bool:
    normalized = str(keyword or "").strip().casefold()
    if not normalized:
        return True
    haystack = " ".join(str(item or "") for item in fields).casefold()
    return normalized in haystack


def _build_feedback_submitter_payload(actor: dict) -> dict:
    return {
        "id": str(actor.get("id") or ""),
        "username": str(actor.get("username") or ""),
        "display_name": str(actor.get("display_name") or actor.get("username") or ""),
        "role": normalize_role(actor.get("role")),
    }


def _serialize_enterprise_request(item: EnterpriseRequest) -> dict:
    return {
        "id": int(item.id),
        "organization_id": item.organization_id,
        "organization_name": item.organization_name,
        "category": item.category,
        "title": item.title,
        "content": item.content,
        "submitter_id": item.submitter_id,
        "submitter_username": item.submitter_username,
        "submitter_display_name": item.submitter_display_name,
        "submitter_role": item.submitter_role,
        "target_user_id": item.target_user_id,
        "target_username": item.target_username,
        "target_display_name": item.target_display_name,
        "target_role": item.target_role,
        "status": item.status,
        "response_note": item.response_note,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _serialize_platform_bug_feedback(item: PlatformBugFeedback) -> dict:
    return {
        "id": int(item.id),
        "category": item.category,
        "title": item.title,
        "content": item.content,
        "submitter_id": item.submitter_id,
        "submitter_username": item.submitter_username,
        "submitter_display_name": item.submitter_display_name,
        "submitter_role": item.submitter_role,
        "status": item.status,
        "response_note": item.response_note,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _enterprise_actor(request) -> dict:
    actor = auth_service.require_actor_capability(request, "feedback.enterprise.submit")
    if not normalize_role(actor.get("role")).startswith("enterprise_"):
        raise_api_error(403, "feedback_enterprise_only")
    organization_id = str(actor.get("organization_id") or "").strip()
    if not organization_id:
        raise_api_error(400, "feedback_enterprise_org_required")
    return actor


def _list_enterprise_recipient_users(actor: dict) -> list:
    organization_id = str(actor.get("organization_id") or "").strip()
    items = []
    for user in list_users():
        if normalize_role(getattr(user, "role", "")).startswith("enterprise_") is False:
            continue
        if str(getattr(user, "organization_id", "") or "").strip() != organization_id:
            continue
        if str(getattr(user, "account_status", "approved") or "approved").lower() == "deactivated":
            continue
        items.append(user)
    items.sort(
        key=lambda item: (
            0 if normalize_role(getattr(item, "role", "")) == "enterprise_admin" else 1,
            str(getattr(item, "display_name", "") or getattr(item, "username", "")).casefold(),
        )
    )
    return items


def list_enterprise_request_recipients(request) -> dict:
    actor = _enterprise_actor(request)
    items = []
    for user in _list_enterprise_recipient_users(actor):
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "role": normalize_role(user.role),
                "organization_id": getattr(user, "organization_id", None),
                "organization_name": getattr(user, "organization_name", None),
            }
        )
    return {"items": items}


def _enterprise_request_items_for_actor(actor: dict) -> list[EnterpriseRequest]:
    organization_id = str(actor.get("organization_id") or "").strip()
    return [
        item
        for item in list_enterprise_requests()
        if str(item.organization_id or "").strip() == organization_id
    ]


def list_enterprise_request_feed(
    request,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = 80,
) -> dict:
    actor = _enterprise_actor(request)
    normalized_status = _normalize_status(status) or "all"
    normalized_category = _normalize_category(category) or "all"
    normalized_search = str(search or "").strip()
    safe_limit = max(1, min(int(limit or 80), 200))

    items = []
    for item in _enterprise_request_items_for_actor(actor):
        if normalized_status != "all" and item.status != normalized_status:
            continue
        if normalized_category != "all" and item.category != normalized_category:
            continue
        if not _match_search(
            [
                item.title,
                item.content,
                item.submitter_display_name,
                item.submitter_username,
                item.target_display_name,
                item.target_username,
            ],
            normalized_search,
        ):
            continue
        items.append(item)

    items.sort(key=lambda item: (item.updated_at, int(item.id)), reverse=True)
    source_items = _enterprise_request_items_for_actor(actor)
    summary = {
        "all": len(source_items),
        "open": sum(1 for item in source_items if item.status == "open"),
        "in_progress": sum(1 for item in source_items if item.status == "in_progress"),
        "resolved": sum(1 for item in source_items if item.status == "resolved"),
        "closed": sum(1 for item in source_items if item.status == "closed"),
    }
    return {
        "items": [_serialize_enterprise_request(item) for item in items[:safe_limit]],
        "summary": summary,
        "status": normalized_status,
        "category": normalized_category,
        "search": normalized_search,
        "limit": safe_limit,
    }


def create_enterprise_request(
    request,
    category: str,
    title: str,
    content: str,
    target_user_id: str,
) -> dict:
    actor = _enterprise_actor(request)
    normalized_category = _normalize_category(category)
    if normalized_category not in ENTERPRISE_REQUEST_CATEGORIES:
        raise_api_error(400, "enterprise_request_category_invalid")
    normalized_title = str(title or "").strip()
    normalized_content = str(content or "").strip()
    normalized_target_user_id = str(target_user_id or "").strip()
    if not normalized_title or not normalized_content or not normalized_target_user_id:
        raise_api_error(400, "enterprise_request_fields_required")

    recipient = next((user for user in _list_enterprise_recipient_users(actor) if str(user.id) == normalized_target_user_id), None)
    if recipient is None:
        raise_api_error(404, "enterprise_request_target_not_found")

    submitter = _build_feedback_submitter_payload(actor)
    timestamp = now_iso()
    item = EnterpriseRequest(
        id=get_next_enterprise_request_id(),
        organization_id=str(actor.get("organization_id") or ""),
        organization_name=str(actor.get("organization_name") or "") or None,
        category=normalized_category,
        title=normalized_title,
        content=normalized_content,
        submitter_id=submitter["id"],
        submitter_username=submitter["username"],
        submitter_display_name=submitter["display_name"],
        submitter_role=submitter["role"],
        target_user_id=str(recipient.id),
        target_username=str(recipient.username),
        target_display_name=str(recipient.display_name),
        target_role=normalize_role(recipient.role),
        status="open",
        response_note=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    saved = upsert_enterprise_request(item)
    record_operation_audit(
        "enterprise_request",
        saved.id,
        "create",
        actor=actor,
        metadata={
            "category": saved.category,
            "target_user_id": saved.target_user_id,
            "target_username": saved.target_username,
            "status": saved.status,
        },
    )
    return {"item": _serialize_enterprise_request(saved)}


def update_enterprise_request_status(
    request,
    request_id: int,
    status: str,
    response_note: str | None = None,
) -> dict:
    actor = _enterprise_actor(request)
    target = get_enterprise_request_by_id(int(request_id or 0))
    if target is None:
        raise_api_error(404, "enterprise_request_not_found")
    if str(target.organization_id or "") != str(actor.get("organization_id") or ""):
        raise_api_error(403, "enterprise_request_scope_denied")

    normalized_status = _normalize_status(status)
    if normalized_status not in FEEDBACK_STATUS_VALUES:
        raise_api_error(400, "feedback_status_invalid")
    actor_role = normalize_role(actor.get("role"))
    actor_id = str(actor.get("id") or "")
    can_manage = actor_role == "enterprise_admin" or actor_id == str(target.target_user_id or "")
    if not can_manage:
        raise_api_error(403, "enterprise_request_manage_denied")

    target.status = normalized_status
    target.response_note = str(response_note or "").strip() or target.response_note
    target.updated_at = now_iso()
    saved = upsert_enterprise_request(target)
    record_operation_audit(
        "enterprise_request",
        saved.id,
        "status.update",
        actor=actor,
        metadata={
            "status": saved.status,
            "response_note": saved.response_note,
        },
    )
    return {"item": _serialize_enterprise_request(saved)}


def _platform_bug_feedback_actor(request, allow_manager: bool = False) -> dict:
    if allow_manager:
        return auth_service.require_actor_capability(request, "feedback.platform.manage")
    return auth_service.require_actor_capability(request, "feedback.platform.submit")


def list_platform_bug_feedback_feed(
    request,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = 80,
) -> dict:
    actor = auth_service.require_authenticated_actor(request)
    actor_role = normalize_role(actor.get("role"))
    can_manage = actor_role == "platform_admin" and auth_service.has_capability(actor.get("role"), "feedback.platform.manage", account_status=actor.get("account_status"))
    if not can_manage and not auth_service.has_capability(actor.get("role"), "feedback.platform.submit", account_status=actor.get("account_status")):
        raise_api_error(403, "feedback_platform_submit_denied")

    normalized_status = _normalize_status(status) or "all"
    normalized_category = _normalize_category(category) or "all"
    normalized_search = str(search or "").strip()
    safe_limit = max(1, min(int(limit or 80), 200))

    source_items = list_platform_bug_feedback()
    if not can_manage:
        source_items = [item for item in source_items if str(item.submitter_id or "") == str(actor.get("id") or "")]

    items = []
    for item in source_items:
        if normalized_status != "all" and item.status != normalized_status:
            continue
        if normalized_category != "all" and item.category != normalized_category:
            continue
        if not _match_search(
            [
                item.title,
                item.content,
                item.submitter_display_name,
                item.submitter_username,
            ],
            normalized_search,
        ):
            continue
        items.append(item)

    items.sort(key=lambda item: (item.updated_at, int(item.id)), reverse=True)
    summary = {
        "all": len(source_items),
        "open": sum(1 for item in source_items if item.status == "open"),
        "in_progress": sum(1 for item in source_items if item.status == "in_progress"),
        "resolved": sum(1 for item in source_items if item.status == "resolved"),
        "closed": sum(1 for item in source_items if item.status == "closed"),
    }
    return {
        "items": [_serialize_platform_bug_feedback(item) for item in items[:safe_limit]],
        "summary": summary,
        "status": normalized_status,
        "category": normalized_category,
        "search": normalized_search,
        "limit": safe_limit,
        "management": can_manage,
    }


def create_platform_bug_feedback(request, category: str, title: str, content: str) -> dict:
    actor = _platform_bug_feedback_actor(request)
    normalized_category = _normalize_category(category)
    if normalized_category not in PLATFORM_BUG_FEEDBACK_CATEGORIES:
        raise_api_error(400, "platform_bug_feedback_category_invalid")
    normalized_title = str(title or "").strip()
    normalized_content = str(content or "").strip()
    if not normalized_title or not normalized_content:
        raise_api_error(400, "platform_bug_feedback_fields_required")

    submitter = _build_feedback_submitter_payload(actor)
    timestamp = now_iso()
    item = PlatformBugFeedback(
        id=get_next_platform_bug_feedback_id(),
        category=normalized_category,
        title=normalized_title,
        content=normalized_content,
        submitter_id=submitter["id"],
        submitter_username=submitter["username"],
        submitter_display_name=submitter["display_name"],
        submitter_role=submitter["role"],
        status="open",
        response_note=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    saved = upsert_platform_bug_feedback(item)
    record_operation_audit(
        "platform_bug_feedback",
        saved.id,
        "create",
        actor=actor,
        metadata={
            "category": saved.category,
            "status": saved.status,
        },
    )
    return {"item": _serialize_platform_bug_feedback(saved)}


def update_platform_bug_feedback_status(
    request,
    feedback_id: int,
    status: str,
    response_note: str | None = None,
) -> dict:
    actor = _platform_bug_feedback_actor(request, allow_manager=True)
    target = get_platform_bug_feedback_by_id(int(feedback_id or 0))
    if target is None:
        raise_api_error(404, "platform_bug_feedback_not_found")
    normalized_status = _normalize_status(status)
    if normalized_status not in FEEDBACK_STATUS_VALUES:
        raise_api_error(400, "feedback_status_invalid")
    target.status = normalized_status
    target.response_note = str(response_note or "").strip() or target.response_note
    target.updated_at = now_iso()
    saved = upsert_platform_bug_feedback(target)
    record_operation_audit(
        "platform_bug_feedback",
        saved.id,
        "status.update",
        actor=actor,
        metadata={
            "status": saved.status,
            "response_note": saved.response_note,
        },
    )
    return {"item": _serialize_platform_bug_feedback(saved)}
