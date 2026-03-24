from __future__ import annotations

from app.models.comfy_job import ComfyRenderJob


comfy_render_jobs: list[ComfyRenderJob] = []


def list_comfy_render_jobs() -> list[ComfyRenderJob]:
    return comfy_render_jobs


def get_comfy_render_job_by_id(job_id: int) -> ComfyRenderJob | None:
    normalized_id = int(job_id or 0)
    return next((job for job in comfy_render_jobs if int(job.id) == normalized_id), None)


def get_next_comfy_render_job_id() -> int:
    return max((int(job.id) for job in comfy_render_jobs), default=0) + 1


def upsert_comfy_render_job(job: ComfyRenderJob) -> ComfyRenderJob:
    existing = get_comfy_render_job_by_id(job.id)
    if existing is None:
        comfy_render_jobs.append(job)
        return job

    comfy_render_jobs[comfy_render_jobs.index(existing)] = job
    return job


def delete_comfy_render_job(job_id: int) -> bool:
    existing = get_comfy_render_job_by_id(job_id)
    if existing is None:
        return False
    comfy_render_jobs.remove(existing)
    return True
