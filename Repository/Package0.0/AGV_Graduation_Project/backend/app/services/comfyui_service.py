from __future__ import annotations

import json
from datetime import datetime
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from app.core.settings import get_settings
from app.models.comfy_job import ComfyRenderJob
from app.repositories.comfy_job_repository import (
    delete_comfy_render_job,
    get_comfy_render_job_by_id,
    get_next_comfy_render_job_id,
    list_comfy_render_jobs,
    upsert_comfy_render_job,
)
from app.services.operation_audit_service import record_operation_audit
from app.utils.api_error import raise_api_error


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _settings():
    return get_settings()


def _base_url() -> str:
    raw = str(_settings().comfyui_base_url or "").strip().rstrip("/")
    return raw or "http://127.0.0.1:8188"


def _timeout_sec() -> int:
    return max(int(_settings().comfyui_timeout_sec), 3)


def _ensure_enabled() -> None:
    if not _settings().comfyui_enabled:
        raise_api_error(503, "comfyui_disabled")


def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url=url, data=data, headers=headers, method=method.upper())
    try:
        with urllib_request.urlopen(req, timeout=_timeout_sec()) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise_api_error(
            502,
            "comfyui_request_failed",
            upstream_status=int(exc.code),
            upstream_detail=detail[:400] if detail else None,
        )
    except urllib_error.URLError as exc:
        raise_api_error(502, "comfyui_unreachable", reason=str(exc.reason))


def _build_prompt_payload(workflow_payload: dict, prompt_text: str | None = None, source_summary: dict | None = None) -> dict:
    normalized_workflow = dict(workflow_payload or {})
    if not normalized_workflow:
        raise_api_error(400, "comfyui_workflow_required")

    payload = dict(normalized_workflow)
    if "prompt" not in payload:
        payload = {"prompt": normalized_workflow}

    payload.setdefault("client_id", f"agv-{uuid4()}")
    extra_data = dict(payload.get("extra_data") or {})
    if prompt_text:
        extra_data["agv_prompt_text"] = str(prompt_text)
    if source_summary:
        extra_data["agv_input_summary"] = source_summary
    if extra_data:
        payload["extra_data"] = extra_data
    return payload


def _list_checkpoint_names() -> list[str]:
    payload = _request_json("GET", f"{_base_url()}/object_info/CheckpointLoaderSimple")
    loader_info = payload.get("CheckpointLoaderSimple") if isinstance(payload, dict) else None
    required = (
        (loader_info or {}).get("input", {}).get("required", {})
        if isinstance(loader_info, dict)
        else {}
    )
    ckpt_info = required.get("ckpt_name")
    if not isinstance(ckpt_info, list) or not ckpt_info:
        return []
    raw_names = ckpt_info[0]
    if not isinstance(raw_names, list):
        return []
    return [str(item) for item in raw_names if str(item).strip()]


def _extract_history_entry(history_payload: dict, prompt_id: str) -> dict | None:
    if not isinstance(history_payload, dict):
        return None
    if prompt_id in history_payload and isinstance(history_payload[prompt_id], dict):
        return history_payload[prompt_id]
    if len(history_payload) == 1:
        only_entry = next(iter(history_payload.values()))
        if isinstance(only_entry, dict):
            return only_entry
    return None


def _extract_asset_urls(prompt_id: str, history_entry: dict) -> list[str]:
    outputs = history_entry.get("outputs") or {}
    asset_urls: list[str] = []
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images") or []:
            if not isinstance(image, dict):
                continue
            filename = image.get("filename")
            if not filename:
                continue
            query = urllib_parse.urlencode(
                {
                    "filename": filename,
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
            )
            asset_urls.append(f"{_base_url()}/view?{query}")
    return asset_urls


def _build_input_summary(
    source_type: str,
    source_ref: str | None,
    input_payload: dict,
    prompt_text: str | None,
    explicit_summary: dict | None,
) -> dict:
    summary = dict(explicit_summary or {})
    summary.setdefault("source_type", str(source_type))
    if source_ref:
        summary.setdefault("source_ref", str(source_ref))
    summary.setdefault("top_level_keys", sorted(input_payload.keys()) if isinstance(input_payload, dict) else [])
    summary.setdefault("prompt_text_length", len(str(prompt_text or "")))
    return summary


def _serialize_job(job: ComfyRenderJob) -> dict:
    return {
        "id": int(job.id),
        "source_type": job.source_type,
        "source_ref": job.source_ref,
        "input_summary": dict(job.input_summary or {}),
        "workflow_payload": dict(job.workflow_payload or {}),
        "status": job.status,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "asset_urls": list(job.asset_urls or []),
        "error_message": job.error_message,
        "prompt_id": job.prompt_id,
    }


def _refresh_job(job: ComfyRenderJob) -> ComfyRenderJob:
    if not job.prompt_id or job.status in {"completed", "failed"}:
        return job

    try:
        history_payload = _request_json("GET", f"{_base_url()}/history/{job.prompt_id}")
    except Exception as exc:
        if getattr(exc, "status_code", None) == 502:
            job.status = "failed"
            job.error_message = str(getattr(exc, "detail", None) or "ComfyUI history request failed")
            job.completed_at = now_iso()
            upsert_comfy_render_job(job)
        return job

    history_entry = _extract_history_entry(history_payload, str(job.prompt_id))
    if history_entry is None:
        if job.status == "submitted":
            job.status = "running"
            upsert_comfy_render_job(job)
        return job

    status_payload = history_entry.get("status") or {}
    status_str = str(status_payload.get("status_str") or "").strip().lower()
    asset_urls = _extract_asset_urls(str(job.prompt_id), history_entry)
    if status_str in {"error", "failed"}:
        job.status = "failed"
        job.error_message = json.dumps(status_payload, ensure_ascii=False)
        job.completed_at = now_iso()
    else:
        job.status = "completed"
        job.asset_urls = asset_urls
        job.completed_at = now_iso()
        job.error_message = None
    upsert_comfy_render_job(job)
    return job


def submit_render_job(
    *,
    source_type: str,
    source_ref: str | None,
    input_payload: dict,
    input_summary: dict | None,
    prompt_text: str | None,
    workflow_payload: dict,
    actor: dict,
) -> dict:
    _ensure_enabled()
    created_at = now_iso()
    summary = _build_input_summary(source_type, source_ref, input_payload, prompt_text, input_summary)
    actor_name = str(actor.get("display_name") or actor.get("username") or "unknown")
    job = ComfyRenderJob(
        id=get_next_comfy_render_job_id(),
        source_type=str(source_type or "custom_json"),
        source_ref=str(source_ref or "").strip() or None,
        input_summary=summary,
        workflow_payload=dict(workflow_payload or {}),
        status="submitted",
        created_by=actor_name,
        created_at=created_at,
        completed_at=None,
        asset_urls=[],
        error_message=None,
        prompt_id=None,
    )

    prompt_payload = _build_prompt_payload(job.workflow_payload, prompt_text=prompt_text, source_summary=summary)

    try:
        prompt_response = _request_json("POST", f"{_base_url()}/prompt", prompt_payload)
        prompt_id = str(prompt_response.get("prompt_id") or "").strip()
        if not prompt_id:
            raise_api_error(502, "comfyui_invalid_response")
        job.prompt_id = prompt_id
        job.status = "submitted"
    except Exception as exc:
        if getattr(exc, "status_code", None):
            job.status = "failed"
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                job.error_message = detail.get("error_code") or json.dumps(detail, ensure_ascii=False)
            else:
                job.error_message = str(detail or exc)
            job.completed_at = now_iso()
        else:
            raise

    upsert_comfy_render_job(job)
    record_operation_audit(
        "comfy_render_job",
        job.id,
        "render",
        actor,
        {
            "source_type": job.source_type,
            "source_ref": job.source_ref,
            "status": job.status,
            "prompt_id": job.prompt_id,
        },
    )
    return {
        "job": _serialize_job(job),
        "comfyui_base_url": _base_url(),
    }


def list_render_jobs(limit: int = 40) -> dict:
    jobs = sorted(list_comfy_render_jobs(), key=lambda item: (item.created_at, int(item.id)), reverse=True)
    refreshed = [_refresh_job(job) for job in jobs[: max(1, min(int(limit or 40), 100))]]
    return {
        "items": [_serialize_job(job) for job in refreshed],
        "limit": max(1, min(int(limit or 40), 100)),
        "comfyui_base_url": _base_url(),
    }


def get_render_job_detail(job_id: int) -> dict:
    job = get_comfy_render_job_by_id(int(job_id or 0))
    if job is None:
        raise_api_error(404, "comfyui_job_not_found")
    refreshed = _refresh_job(job)
    return {
        "job": _serialize_job(refreshed),
        "comfyui_base_url": _base_url(),
    }


def list_render_assets() -> dict:
    jobs = sorted(list_comfy_render_jobs(), key=lambda item: (item.created_at, int(item.id)), reverse=True)
    assets = []
    for job in jobs:
        refreshed = _refresh_job(job)
        for index, asset_url in enumerate(refreshed.asset_urls or []):
            assets.append(
                {
                    "job_id": int(refreshed.id),
                    "source_type": refreshed.source_type,
                    "source_ref": refreshed.source_ref,
                    "created_by": refreshed.created_by,
                    "created_at": refreshed.created_at,
                    "asset_url": asset_url,
                    "asset_index": index,
                }
            )
    return {
        "items": assets,
        "count": len(assets),
        "comfyui_base_url": _base_url(),
    }


def list_available_checkpoints() -> dict:
    _ensure_enabled()
    names = _list_checkpoint_names()
    preferred = next(
        (name for name in names if name == "DreamShaper_8_pruned.safetensors"),
        names[0] if names else None,
    )
    return {
        "items": names,
        "count": len(names),
        "preferred": preferred,
        "comfyui_base_url": _base_url(),
    }


def delete_render_job(job_id: int, actor: dict) -> dict:
    job = get_comfy_render_job_by_id(int(job_id or 0))
    if job is None:
        raise_api_error(404, "comfyui_job_not_found")

    deleted = delete_comfy_render_job(int(job_id))
    if not deleted:
        raise_api_error(404, "comfyui_job_not_found")

    record_operation_audit(
        "comfy_render_job",
        int(job_id),
        "delete",
        actor,
        {
            "source_type": job.source_type,
            "source_ref": job.source_ref,
            "status": job.status,
            "prompt_id": job.prompt_id,
        },
    )
    return {
        "ok": True,
        "job_id": int(job_id),
        "deleted_record_only": True,
        "message": "ComfyUI render job record deleted.",
    }
