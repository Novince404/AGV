from fastapi import APIRouter, Query, Request

from app.schemas.auth import (
    EnterpriseRequestCreateRequest,
    EnterpriseRequestStatusRequest,
    PlatformBugFeedbackCreateRequest,
    PlatformBugFeedbackStatusRequest,
)
from app.services import feedback_service


router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("/enterprise/recipients")
def list_enterprise_request_recipients(request: Request):
    return feedback_service.list_enterprise_request_recipients(request)


@router.get("/enterprise/requests")
def list_enterprise_requests(
    request: Request,
    status: str | None = Query(default="all"),
    category: str | None = Query(default="all"),
    search: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
):
    return feedback_service.list_enterprise_request_feed(
        request,
        status=status,
        category=category,
        search=search,
        limit=limit,
    )


@router.post("/enterprise/requests")
def create_enterprise_request(request: Request, req: EnterpriseRequestCreateRequest):
    return feedback_service.create_enterprise_request(
        request,
        category=req.category,
        title=req.title,
        content=req.content,
        target_user_id=req.target_user_id,
    )


@router.post("/enterprise/requests/{request_id}/status")
def update_enterprise_request_status(request: Request, request_id: int, req: EnterpriseRequestStatusRequest):
    return feedback_service.update_enterprise_request_status(
        request,
        request_id=request_id,
        status=req.status,
        response_note=req.response_note,
    )


@router.get("/platform-bugs")
def list_platform_bug_feedback(
    request: Request,
    status: str | None = Query(default="all"),
    category: str | None = Query(default="all"),
    search: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
):
    return feedback_service.list_platform_bug_feedback_feed(
        request,
        status=status,
        category=category,
        search=search,
        limit=limit,
    )


@router.post("/platform-bugs")
def create_platform_bug_feedback(request: Request, req: PlatformBugFeedbackCreateRequest):
    return feedback_service.create_platform_bug_feedback(
        request,
        category=req.category,
        title=req.title,
        content=req.content,
    )


@router.post("/platform-bugs/{feedback_id}/status")
def update_platform_bug_feedback_status(
    request: Request,
    feedback_id: int,
    req: PlatformBugFeedbackStatusRequest,
):
    return feedback_service.update_platform_bug_feedback_status(
        request,
        feedback_id=feedback_id,
        status=req.status,
        response_note=req.response_note,
    )
