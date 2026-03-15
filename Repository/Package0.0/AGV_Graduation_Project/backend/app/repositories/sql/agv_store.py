"""Temporary SQL AGV adapter.

Current behavior intentionally proxies to the memory implementation to keep
demo/runtime behavior unchanged during the A3 repository migration.
"""

from app.repositories.memory.agv_store import agv_list, get_agv_by_id, get_first_idle_agv, list_agvs, list_idle_agvs

__all__ = [
    "agv_list",
    "get_agv_by_id",
    "get_first_idle_agv",
    "list_agvs",
    "list_idle_agvs",
]
