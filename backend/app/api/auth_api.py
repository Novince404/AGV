from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from app.schemas.auth import (
    AuthLoginRequest,
    AuthPasswordChangeRequest,
    EnterpriseMemberCreateRequest,
    EnterpriseApplicationReviewRequest,
    EnterpriseRegisterRequest,
    PersonalRegisterRequest,
    UserDeactivateRequest,
    UserSuspendRequest,
)
from app.services import auth_service
from app.core.auth_security import issue_csrf_token, utc_timestamp
from app.core.settings import get_settings
from app.core.oidc_client import begin_oidc_login, exchange_oidc_callback, oidc_configuration_status
from app.schemas.oidc import OIDCLinkReviewRequest, OIDCRejectRequest
from app.services import oidc_service


router = APIRouter(prefix="/auth", tags=["Auth"])


def _apply_auth_cookies(request: Request, response: Response, payload: dict) -> dict:
    raw_token = str(payload.get("session_token") or "")
    if not raw_token:
        return payload
    settings = get_settings()
    max_age = max(int(payload.get("session_expires_at") or 0) - utc_timestamp(), 300)
    csrf_token = issue_csrf_token()
    response.set_cookie(
        "agv_session",
        raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "agv_csrf",
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    result = dict(payload)
    result["csrf_token"] = csrf_token
    if request.url.path.startswith("/api/v1/"):
        result.pop("session_token", None)
    return result


@router.post("/login")
def login(req: AuthLoginRequest, request: Request, response: Response):
    client_host = request.client.host if request.client else "unknown"
    payload = auth_service.login(req.username, req.password, client_key=client_host)
    return _apply_auth_cookies(request, response, payload)


@router.post("/logout")
def logout(request: Request, response: Response):
    payload = auth_service.logout(request)
    response.delete_cookie("agv_session", path="/")
    response.delete_cookie("agv_csrf", path="/")
    return payload


@router.post("/change-password")
def change_password(req: AuthPasswordChangeRequest, request: Request, response: Response):
    payload = auth_service.change_password(request, req.current_password, req.new_password)
    return _apply_auth_cookies(request, response, payload)


@router.get("/me")
def get_current_auth(request: Request):
    return auth_service.get_current_auth(request)


@router.get("/oidc/status")
def oidc_status():
    return oidc_configuration_status()


@router.get("/oidc/login")
async def oidc_login(request: Request):
    return await begin_oidc_login(request)


@router.get("/oidc/callback", name="oidc_callback")
async def oidc_callback(request: Request):
    claims = await exchange_oidc_callback(request)
    result = oidc_service.complete_external_login(claims)
    settings = get_settings()
    if result["status"] == "authenticated":
        response = RedirectResponse(f"{settings.frontend_base_url}/login?oidc=success", status_code=303)
        _apply_auth_cookies(request, response, result["auth"])
        return response
    query = urlencode({"oidc": "pending", "request_id": result["request"]["id"]})
    return RedirectResponse(f"{settings.frontend_base_url}/login?{query}", status_code=303)


@router.get("/oidc/link-requests")
def oidc_link_requests(request: Request, status: str | None = Query(default="pending")):
    return oidc_service.list_requests(request, status=status)


@router.post("/oidc/link-requests/{request_id}/approve")
def approve_oidc_link(request: Request, request_id: str, req: OIDCLinkReviewRequest):
    return oidc_service.approve_request(request, request_id, req.user_id)


@router.post("/oidc/link-requests/{request_id}/reject")
def reject_oidc_link(request: Request, request_id: str, req: OIDCRejectRequest):
    return oidc_service.reject_request(request, request_id, req.note)


@router.get("/operations")
def get_operation_feed(
    request: Request,
    limit: int = Query(default=60, ge=1, le=200),
    resource_type: str | None = None,
    action: str | None = None,
):
    auth_service.require_actor_capability(request, "audit.view")
    return auth_service.list_operation_feed(limit=limit, resource_type=resource_type, action=action)


@router.delete("/operations/{audit_id}")
def delete_operation_feed_item(request: Request, audit_id: int):
    return auth_service.delete_operation_feed_item(request, audit_id)


@router.post("/register-enterprise")
def register_enterprise(req: EnterpriseRegisterRequest):
    return auth_service.register_enterprise(
        company_name=req.company_name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        username=req.username,
        password=req.password,
    )


@router.post("/register-personal")
def register_personal(req: PersonalRegisterRequest, request: Request, response: Response):
    payload = auth_service.register_personal(
        username=req.username,
        password=req.password,
        display_name=req.display_name,
    )
    return _apply_auth_cookies(request, response, payload)


@router.get("/users")
def list_users(
    request: Request,
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
):
    auth_service.require_actor_capability(request, "system.manage")
    return auth_service.list_user_feed(role=role, status=status, search=search, limit=limit)


@router.get("/users/{user_id}")
def get_user_detail(request: Request, user_id: str):
    auth_service.require_actor_capability(request, "system.manage")
    return auth_service.get_user_detail(user_id)


@router.get("/users/export")
def export_users(
    request: Request,
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    return auth_service.export_user_feed(request, role=role, status=status, search=search)


@router.get("/enterprise-members")
def list_enterprise_members(request: Request):
    return auth_service.list_enterprise_members(request)


@router.post("/enterprise-members")
def create_enterprise_member(request: Request, req: EnterpriseMemberCreateRequest):
    return auth_service.create_enterprise_member(
        request,
        username=req.username,
        password=req.password,
        display_name=req.display_name,
        role=req.role,
    )


@router.post("/users/{user_id}/suspend")
def suspend_user(request: Request, user_id: str, req: UserSuspendRequest):
    return auth_service.suspend_user_account(
        request,
        user_id=user_id,
        reason=req.reason,
        note=req.note,
        duration_days=req.duration_days,
        permanent=req.permanent,
    )


@router.post("/users/{user_id}/unsuspend")
def unsuspend_user(request: Request, user_id: str):
    return auth_service.unsuspend_user_account(request, user_id=user_id)


@router.post("/users/{user_id}/deactivate")
def deactivate_user(request: Request, user_id: str, req: UserDeactivateRequest):
    return auth_service.deactivate_user_account(
        request,
        user_id=user_id,
        reason=req.reason,
        note=req.note,
    )


@router.get("/enterprise-applications")
def list_enterprise_applications(
    request: Request,
    status: str | None = Query(default="all"),
):
    auth_service.require_actor_capability(request, "enterprise.approve")
    return auth_service.list_enterprise_application_feed(status=status)


@router.get("/enterprise-applications/{application_id}")
def get_enterprise_application_detail(request: Request, application_id: int):
    auth_service.require_actor_capability(request, "enterprise.approve")
    return auth_service.get_enterprise_application_detail(application_id)


@router.post("/enterprise-applications/{application_id}/approve")
def approve_enterprise_application(
    request: Request,
    application_id: int,
    req: EnterpriseApplicationReviewRequest,
):
    return auth_service.review_enterprise_application(
        request=request,
        application_id=application_id,
        decision="approve",
        review_note=req.review_note,
    )


@router.post("/enterprise-applications/{application_id}/reject")
def reject_enterprise_application(
    request: Request,
    application_id: int,
    req: EnterpriseApplicationReviewRequest,
):
    return auth_service.review_enterprise_application(
        request=request,
        application_id=application_id,
        decision="reject",
        review_note=req.review_note,
    )
