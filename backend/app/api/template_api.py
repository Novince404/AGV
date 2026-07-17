from fastapi import APIRouter, Request

from app.schemas.template import TaskTemplateUpsertRequest
from app.services import auth_service, template_service


router = APIRouter(prefix="/template", tags=["Template"])


@router.get("/list")
def get_templates():
    return template_service.get_template_list()


@router.post("/upsert")
def upsert_template(req: TaskTemplateUpsertRequest, request: Request):
    auth_service.require_actor_capability(request, "template.write")
    return template_service.create_or_update_template(req)


@router.delete("/{template_id}")
def delete_template(template_id: str, request: Request):
    auth_service.require_actor_capability(request, "template.write")
    return template_service.delete_template(template_id)
