from __future__ import annotations

from app.models.enterprise_application import EnterpriseApplication


enterprise_application_list: list[EnterpriseApplication] = []


def list_enterprise_applications() -> list[EnterpriseApplication]:
    return enterprise_application_list


def get_enterprise_application_by_id(application_id: int) -> EnterpriseApplication | None:
    target_id = int(application_id or 0)
    return next((item for item in enterprise_application_list if int(item.id) == target_id), None)


def get_enterprise_application_by_username(username: str) -> EnterpriseApplication | None:
    normalized = str(username or "").strip().casefold()
    if not normalized:
        return None
    return next((item for item in enterprise_application_list if item.username.casefold() == normalized), None)


def get_enterprise_application_by_user_id(user_id: str) -> EnterpriseApplication | None:
    normalized = str(user_id or "").strip()
    if not normalized:
        return None
    return next((item for item in enterprise_application_list if item.user_id == normalized), None)


def get_next_enterprise_application_id() -> int:
    return max((int(item.id) for item in enterprise_application_list), default=0) + 1


def upsert_enterprise_application(application: EnterpriseApplication) -> EnterpriseApplication:
    existing = get_enterprise_application_by_id(application.id)
    if existing is None:
        enterprise_application_list.append(application)
        return application
    enterprise_application_list[enterprise_application_list.index(existing)] = application
    return application
