from __future__ import annotations

from uuid import uuid4

from fastapi import Request

from app.models.oidc import OIDCIdentity, OIDCLinkRequest
from app.repositories.auth_repository import get_user_by_id
from app.repositories.oidc_repository import (
    get_identity,
    get_link_request,
    get_pending_request,
    list_link_requests,
    upsert_identity,
    upsert_link_request,
)
from app.services import auth_service
from app.services.operation_audit_service import now_iso, record_operation_audit
from app.utils.api_error import raise_api_error


def complete_external_login(claims: dict) -> dict:
    issuer = str(claims.get("issuer") or "").strip()
    subject = str(claims.get("subject") or "").strip()
    if not issuer or not subject:
        raise_api_error(401, "oidc_claims_invalid")
    identity = get_identity(issuer, subject)
    if identity:
        return {"status": "authenticated", "auth": auth_service.create_external_session(identity.user_id)}

    pending = get_pending_request(issuer, subject)
    if pending is None:
        pending = OIDCLinkRequest(
            id=uuid4().hex,
            issuer=issuer,
            subject=subject,
            email=claims.get("email"),
            display_name=claims.get("display_name"),
            status="pending",
            requested_at=now_iso(),
        )
        pending = upsert_link_request(pending)
        record_operation_audit(
            "oidc_link_request",
            pending.id,
            "oidc.link.requested",
            actor={"id": "oidc_pending", "username": pending.email or pending.subject, "role": "guest", "authenticated": False},
            metadata={"issuer": pending.issuer, "email": pending.email},
        )
    return {"status": "pending", "request": pending.model_dump()}


def list_requests(request: Request, status: str | None = "pending") -> dict:
    auth_service.require_authenticated_actor(request, allowed_roles={"platform_admin", "enterprise_admin"})
    return {"items": [item.model_dump() for item in list_link_requests(status)]}


def approve_request(request: Request, request_id: str, user_id: str) -> dict:
    actor = auth_service.require_authenticated_actor(request, allowed_roles={"platform_admin", "enterprise_admin"})
    item = get_link_request(request_id)
    if item is None:
        raise_api_error(404, "oidc_link_request_not_found")
    if item.status != "pending":
        raise_api_error(409, "oidc_link_request_already_reviewed")
    target = get_user_by_id(str(user_id or "").strip())
    if target is None or not target.active:
        raise_api_error(404, "auth_user_not_found")
    if actor.get("role") == "enterprise_admin":
        if str(actor.get("organization_id") or "") != str(target.organization_id or ""):
            raise_api_error(403, "auth_permission_denied")
    timestamp = now_iso()
    identity = upsert_identity(
        OIDCIdentity(
            issuer=item.issuer,
            subject=item.subject,
            user_id=target.id,
            email=item.email,
            created_at=timestamp,
        )
    )
    item.status = "approved"
    item.reviewed_at = timestamp
    item.reviewed_by = str(actor.get("id") or actor.get("username"))
    item.user_id = target.id
    upsert_link_request(item)
    record_operation_audit(
        "oidc_link_request",
        item.id,
        "oidc.link.approved",
        actor=actor,
        metadata={"user_id": target.id, "issuer": item.issuer, "identity_id": identity.id},
    )
    return {"item": item.model_dump(), "identity": identity.model_dump()}


def reject_request(request: Request, request_id: str, note: str | None = None) -> dict:
    actor = auth_service.require_authenticated_actor(request, allowed_roles={"platform_admin", "enterprise_admin"})
    item = get_link_request(request_id)
    if item is None:
        raise_api_error(404, "oidc_link_request_not_found")
    if item.status != "pending":
        raise_api_error(409, "oidc_link_request_already_reviewed")
    item.status = "rejected"
    item.reviewed_at = now_iso()
    item.reviewed_by = str(actor.get("id") or actor.get("username"))
    upsert_link_request(item)
    record_operation_audit(
        "oidc_link_request",
        item.id,
        "oidc.link.rejected",
        actor=actor,
        metadata={"issuer": item.issuer, "note": str(note or "") or None},
    )
    return {"item": item.model_dump()}
