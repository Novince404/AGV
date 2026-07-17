from __future__ import annotations

from http import HTTPStatus

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


PROBLEM_MEDIA_TYPE = "application/problem+json"


def _title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request failed"


def problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    detail: str,
    errors: list[dict] | None = None,
) -> JSONResponse:
    body: dict = {
        "type": f"https://github.com/Novince404/AGV/problems/{code}",
        "title": _title(status_code),
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status_code, content=body, media_type=PROBLEM_MEDIA_TYPE)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = str(
            exc.detail.get("code")
            or exc.detail.get("error_code")
            or exc.detail.get("error")
            or "request_failed"
        )
        detail = str(exc.detail.get("message") or exc.detail.get("detail") or code)
        errors = exc.detail.get("errors") if isinstance(exc.detail.get("errors"), list) else None
    else:
        code = "request_failed"
        detail = str(exc.detail)
        errors = None
    response = problem_response(
        request,
        status_code=exc.status_code,
        code=code,
        detail=detail,
        errors=errors,
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "location": list(error.get("loc", ())),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    return problem_response(
        request,
        status_code=422,
        code="validation_failed",
        detail="Request validation failed.",
        errors=errors,
    )
