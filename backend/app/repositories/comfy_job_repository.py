"""Public ComfyUI render-job repository facade."""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import comfy_job_store as _store
else:
    from app.repositories.memory import comfy_job_store as _store


def list_comfy_render_jobs():
    return _store.list_comfy_render_jobs()


def get_comfy_render_job_by_id(job_id: int):
    return _store.get_comfy_render_job_by_id(job_id)


def get_next_comfy_render_job_id():
    return _store.get_next_comfy_render_job_id()


def upsert_comfy_render_job(job):
    return _store.upsert_comfy_render_job(job)


def delete_comfy_render_job(job_id: int):
    return _store.delete_comfy_render_job(job_id)


__all__ = [
    "get_comfy_render_job_by_id",
    "get_next_comfy_render_job_id",
    "list_comfy_render_jobs",
    "upsert_comfy_render_job",
    "delete_comfy_render_job",
]
