from __future__ import annotations

from app.core.data_scope import get_current_scope_key
from app.models.agv import AGV


agv_list = [
    AGV(id=1, x=2, y=3, status="idle"),
    AGV(id=2, x=5, y=7, status="idle"),
    AGV(id=3, x=1, y=4, status="idle"),
]

_agv_lists_by_scope: dict[str, list[AGV]] = {}
_next_id = max((item.id for item in agv_list), default=0)


def _current_scope() -> str:
    return get_current_scope_key()


def _clone_default_agvs(scope_key: str) -> list[AGV]:
    return [AGV(**{**item.model_dump(), "scope_key": scope_key}) for item in agv_list]


def _scope_cache(scope_key: str | None = None) -> list[AGV]:
    normalized_scope = str(scope_key or _current_scope())
    if normalized_scope not in _agv_lists_by_scope:
        _agv_lists_by_scope[normalized_scope] = _clone_default_agvs(normalized_scope)
    return _agv_lists_by_scope[normalized_scope]


def list_agvs() -> list[AGV]:
    return _scope_cache()


def get_agv_by_id(agv_id: int) -> AGV | None:
    return next((agv for agv in _scope_cache() if agv.id == agv_id), None)


def list_idle_agvs() -> list[AGV]:
    return [agv for agv in _scope_cache() if agv.status in {"idle", "idle_returning"}]


def get_first_idle_agv() -> AGV | None:
    return next((agv for agv in _scope_cache() if agv.status in {"idle", "idle_returning"}), None)


def create_agv(agv: AGV) -> AGV:
    global _next_id
    _next_id += 1
    created = AGV(**{**agv.model_dump(), "id": _next_id, "scope_key": _current_scope()})
    _scope_cache().append(created)
    return created


def delete_agv(agv_id: int) -> AGV | None:
    target = get_agv_by_id(agv_id)
    if target is None:
        return None
    cache = _scope_cache()
    cache[:] = [agv for agv in cache if agv.id != agv_id]
    return target
