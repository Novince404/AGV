"""Public AGV repository facade.

This facade is the stable import target for service/utils layers.
The concrete implementation is selected by backend runtime mode.
"""

from app.repositories.runtime import is_sql_backend

if is_sql_backend():
    from app.repositories.sql import agv_store as _store
else:
    from app.repositories.memory import agv_store as _store


agv_list = _store.agv_list


def list_agvs():
    return _store.list_agvs()


def get_agv_by_id(agv_id: int):
    return _store.get_agv_by_id(agv_id)


def list_idle_agvs():
    return _store.list_idle_agvs()


def get_first_idle_agv():
    return _store.get_first_idle_agv()


def create_agv(agv):
    return _store.create_agv(agv)


def delete_agv(agv_id: int):
    return _store.delete_agv(agv_id)


__all__ = [
    "agv_list",
    "create_agv",
    "delete_agv",
    "get_agv_by_id",
    "get_first_idle_agv",
    "list_agvs",
    "list_idle_agvs",
]
