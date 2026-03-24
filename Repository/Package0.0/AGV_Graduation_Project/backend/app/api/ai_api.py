from fastapi import APIRouter, Query, Request

from app.schemas.ai import ComfyRenderRequest
from app.services import auth_service
from app.services import comfyui_service


router = APIRouter(prefix="/ai/comfyui", tags=["AI"])


@router.post("/render")
def submit_comfy_render(request: Request, req: ComfyRenderRequest):
    actor = auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.submit_render_job(
        source_type=req.source_type,
        source_ref=req.source_ref,
        input_payload=req.input_payload,
        input_summary=req.input_summary,
        prompt_text=req.prompt_text,
        workflow_payload=req.workflow_payload,
        actor=actor,
    )


@router.get("/jobs")
def list_comfy_render_jobs(
    request: Request,
    limit: int = Query(default=40, ge=1, le=100),
):
    auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.list_render_jobs(limit=limit)


@router.get("/jobs/{job_id}")
def get_comfy_render_job_detail(request: Request, job_id: int):
    auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.get_render_job_detail(job_id)


@router.delete("/jobs/{job_id}")
def delete_comfy_render_job(request: Request, job_id: int):
    actor = auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.delete_render_job(job_id, actor)


@router.get("/assets")
def list_comfy_render_assets(request: Request):
    auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.list_render_assets()


@router.get("/checkpoints")
def list_comfy_checkpoints(request: Request):
    auth_service.require_actor_capability(request, "ai.render")
    return comfyui_service.list_available_checkpoints()
