from fastapi import APIRouter, Query, Request

from app.schemas.auth import AuthLoginRequest, EnterpriseApplicationReviewRequest, EnterpriseRegisterRequest
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


@router.post("/register-enterprise")
def register_enterprise(req: EnterpriseRegisterRequest):
    return auth_service.register_enterprise(
        company_name=req.company_name,
        contact_name=req.contact_name,
        contact_email=req.contact_email,
        username=req.username,
        password=req.password,
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
