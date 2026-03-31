from __future__ import annotations

from app.models.enterprise_request import EnterpriseRequest


enterprise_requests: list[EnterpriseRequest] = []


def list_enterprise_requests() -> list[EnterpriseRequest]:
    return enterprise_requests


def get_enterprise_request_by_id(request_id: int) -> EnterpriseRequest | None:
    normalized_id = int(request_id or 0)
    return next((item for item in enterprise_requests if int(item.id) == normalized_id), None)


def get_next_enterprise_request_id() -> int:
    return max((int(item.id) for item in enterprise_requests), default=0) + 1


def upsert_enterprise_request(item: EnterpriseRequest) -> EnterpriseRequest:
    existing = get_enterprise_request_by_id(item.id)
    if existing is None:
        enterprise_requests.append(item)
        return item
    enterprise_requests[enterprise_requests.index(existing)] = item
    return item
