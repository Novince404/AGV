from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.comfy_job import ComfyRenderJob
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import ComfyRenderJobEntity


comfy_render_jobs: list[ComfyRenderJob] = []
_loaded = False


def _bind_job(job: ComfyRenderJob) -> ComfyRenderJob:
    job.bind_on_change(lambda job_id=job.id: _persist_cached_job(job_id))
    return job


def _entity_to_model(entity: ComfyRenderJobEntity) -> ComfyRenderJob:
    return ComfyRenderJob(
        id=int(entity.id),
        source_type=entity.source_type,
        source_ref=entity.source_ref,
        input_summary=dict(entity.input_summary or {}),
        workflow_payload=dict(entity.workflow_payload or {}),
        status=entity.status,
        created_by=entity.created_by,
        created_at=entity.created_at,
        completed_at=entity.completed_at,
        asset_urls=[str(item) for item in (entity.asset_urls or [])],
        error_message=entity.error_message,
        prompt_id=entity.prompt_id,
    )


def _model_to_entity(job: ComfyRenderJob, entity: ComfyRenderJobEntity | None = None) -> ComfyRenderJobEntity:
    entity = entity or ComfyRenderJobEntity(id=int(job.id))
    entity.source_type = job.source_type
    entity.source_ref = job.source_ref
    entity.input_summary = dict(job.input_summary or {})
    entity.workflow_payload = dict(job.workflow_payload or {})
    entity.status = job.status
    entity.created_by = job.created_by
    entity.created_at = job.created_at
    entity.completed_at = job.completed_at
    entity.asset_urls = list(job.asset_urls or [])
    entity.error_message = job.error_message
    entity.prompt_id = job.prompt_id
    return entity


def _persist_cached_job(job_id: int) -> None:
    job = next((item for item in comfy_render_jobs if int(item.id) == int(job_id)), None)
    if job is None:
        return
    with get_db_session() as session:
        entity = session.get(ComfyRenderJobEntity, int(job.id))
        session.add(_model_to_entity(job, entity))
        session.commit()


def _load_cache() -> None:
    with get_db_session() as session:
        entities = session.execute(select(ComfyRenderJobEntity).order_by(ComfyRenderJobEntity.id)).scalars().all()
    comfy_render_jobs[:] = [_bind_job(_entity_to_model(entity)) for entity in entities]


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    create_all_tables()
    _load_cache()
    _loaded = True


def list_comfy_render_jobs() -> list[ComfyRenderJob]:
    _ensure_loaded()
    return comfy_render_jobs


def get_comfy_render_job_by_id(job_id: int) -> ComfyRenderJob | None:
    _ensure_loaded()
    normalized_id = int(job_id or 0)
    return next((job for job in comfy_render_jobs if int(job.id) == normalized_id), None)


def get_next_comfy_render_job_id() -> int:
    _ensure_loaded()
    return max((int(job.id) for job in comfy_render_jobs), default=0) + 1


def upsert_comfy_render_job(job: ComfyRenderJob) -> ComfyRenderJob:
    _ensure_loaded()
    existing = get_comfy_render_job_by_id(job.id)
    bound = _bind_job(job)
    if existing is None:
        comfy_render_jobs.append(bound)
    else:
        comfy_render_jobs[comfy_render_jobs.index(existing)] = bound
    _persist_cached_job(bound.id)
    return bound


def delete_comfy_render_job(job_id: int) -> bool:
    _ensure_loaded()
    existing = get_comfy_render_job_by_id(job_id)
    if existing is None:
        return False

    comfy_render_jobs.remove(existing)
    with get_db_session() as session:
        entity = session.get(ComfyRenderJobEntity, int(job_id))
        if entity is not None:
            session.delete(entity)
            session.commit()
    return True
