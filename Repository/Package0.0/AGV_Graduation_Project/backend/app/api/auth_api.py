from fastapi import APIRouter, Query, Request

from app.schemas.auth import (
    AuthLoginRequest,
    EnterpriseMemberCreateRequest,
    EnterpriseApplicationReviewRequest,
    EnterpriseRegisterRequest,
    PersonalRegisterRequest,
    UserDeactivateRequest,
    UserSuspendRequest,
)
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(req: AuthLoginRequest):
    return auth_service.login(req.username, req.password)


@router.post("/logout")
def logout(request: Request):
    return auth_service.logout(request)


@router.get("/me")
def get_current_auth(request: Request):
    return auth_service.get_current_auth(request)


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
def register_personal(req: PersonalRegisterRequest):
    return auth_service.register_personal(
        username=req.username,
        password=req.password,
        display_name=req.display_name,
    )


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
