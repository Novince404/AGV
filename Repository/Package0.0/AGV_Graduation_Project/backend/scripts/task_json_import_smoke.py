from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
DEMO_JSON_DIR = REPO_ROOT / "demo" / "json"
SMOKE_DB_PATH = BACKEND_DIR / "agv_task_json_import_smoke.db"
SMOKE_DB_URL = f"sqlite:///{SMOKE_DB_PATH.as_posix()}"

os.environ["AGV_DATA_BACKEND"] = "sqlite"
os.environ["AGV_DATABASE_URL"] = SMOKE_DB_URL
os.environ["AGV_DATABASE_AUTO_CREATE"] = "true"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import dispose_engine  # noqa: E402
from app.core.data_scope import build_scope_key_from_actor, use_scope  # noqa: E402
from app.core.lifecycle import initialize_runtime  # noqa: E402
from app.repositories.agv_repository import get_agv_by_id, list_agvs  # noqa: E402
from app.repositories.task_repository import get_task_by_id  # noqa: E402
from app.services import schedule_service, status_service, task_service  # noqa: E402


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def cleanup_db_file() -> None:
    try:
        dispose_engine()
    except Exception:
        pass
    if not SMOKE_DB_PATH.exists():
        return
    for _ in range(10):
        try:
            SMOKE_DB_PATH.unlink()
            return
        except PermissionError:
            time.sleep(0.2)


def read_demo_tasks(file_name: str) -> list[dict]:
    payload = json.loads((DEMO_JSON_DIR / file_name).read_text(encoding="utf-8"))
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    expect(isinstance(tasks, list) and len(tasks) > 0, f"{file_name} did not contain any tasks")
    return tasks


def build_actor(actor_id: str) -> dict[str, str]:
    return {
        "id": actor_id,
        "username": actor_id,
        "role": "personal",
    }


def wait_for_task_finish(task_id: int, *, timeout_sec: float = 12.0, interval_sec: float = 0.1):
    deadline = time.time() + timeout_sec
    last_task = get_task_by_id(task_id)
    while time.time() < deadline:
        task = get_task_by_id(task_id)
        if task is None:
            raise AssertionError(f"task {task_id} disappeared during json import smoke")
        last_task = task
        if str(task.status) == "finished":
            return task
        time.sleep(interval_sec)
    raise AssertionError(f"task {task_id} did not finish in time, last_status={getattr(last_task, 'status', None)}")


def import_task_items(task_items: list[dict], actor: dict) -> list[int]:
    result = task_service.import_tasks(task_items, actor)
    task_ids = [int(task_id) for task_id in result["task_ids"]]
    expect(len(task_ids) == len(task_items), "json import count mismatch")
    return task_ids


def import_demo_tasks(file_name: str, actor: dict) -> tuple[list[int], list[dict]]:
    task_items = read_demo_tasks(file_name)
    return import_task_items(task_items, actor), task_items


def assert_auto_single_import() -> None:
    actor = build_actor("json_import_auto")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.reset_map_layout()
        scoped_agvs = list_agvs()
        expect(len(scoped_agvs) >= 1, "auto json import smoke requires at least one seeded AGV")

        task_ids, task_items = import_demo_tasks("task_auto_single_demo.json", actor)
        imported_task = get_task_by_id(task_ids[0])
        expect(imported_task is not None, "auto json import task missing after import")
        expect(str(imported_task.dispatch_mode or "") == "auto", "auto json import did not preserve dispatch_mode=auto")
        expect(int(imported_task.priority) == int(task_items[0]["priority"]), "auto json import priority mismatch")

        schedule_data = schedule_service.schedule_task_with_path(
            imported_task.id,
            None,
            "auto",
            str(imported_task.dispatch_algorithm or "simple"),
            int(task_items[0].get("grid_cols") or 10),
            int(task_items[0].get("grid_rows") or 8),
            actor=actor,
        )
        expect(schedule_data["task"]["dispatch_mode"] == "auto", "auto json import did not schedule in auto mode")
        expect(schedule_data["task"]["agv_id"] is not None, "auto json import did not bind an AGV")
        expect(schedule_data["path"], "auto json import schedule returned an empty path")

        finished_task = wait_for_task_finish(imported_task.id)
        expect(
            finished_task.path_to_start is None and finished_task.path_to_end is None,
            "auto json import task retained path fields after finish",
        )


def assert_manual_single_import_waits_for_binding() -> None:
    actor = build_actor("json_import_manual")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.reset_map_layout()
        task_ids, task_items = import_demo_tasks("task_manual_single_demo.json", actor)

        imported_task = get_task_by_id(task_ids[0])
        expect(imported_task is not None, "manual json import task missing after import")
        expect(str(imported_task.dispatch_mode or "") == "manual", "manual json import did not preserve dispatch_mode=manual")
        expect(imported_task.preferred_agv_id is None, "manual json import demo should stay unbound for acceptance")
        expect(imported_task.agv_id is None, "manual json import demo should not auto-bind an AGV")
        expect(str(imported_task.status or "") == "pending", "manual json import demo should remain pending for AGV binding")
        expect(
            str(imported_task.dispatch_reason or "") == str(task_items[0]["dispatch_reason"]),
            "manual json import lost dispatch_reason",
        )


def assert_manual_bound_import_origin_resolution() -> None:
    actor = build_actor("json_import_manual_bound")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.reset_map_layout()
        task_items = [
            {
                "start_x": 2,
                "start_y": 4,
                "end_x": 2,
                "end_y": 5,
                "grid_cols": 10,
                "grid_rows": 8,
                "priority": 2,
                "dispatch_mode": "manual",
                "preferred_agv_id": 1,
                "dispatch_origin_x": 2,
                "dispatch_origin_y": 3,
                "dispatch_algorithm": "simple",
                "dispatch_reason": "Bound manual import smoke.",
            }
        ]
        task_ids = import_task_items(task_items, actor)
        imported_task = get_task_by_id(task_ids[0])
        expect(imported_task is not None, "bound manual json import task missing after import")
        expect(str(imported_task.dispatch_mode or "") == "manual", "bound manual json import lost manual mode")
        expect(
            int(imported_task.dispatch_origin_x or -1) == 2 and int(imported_task.dispatch_origin_y or -1) == 3,
            "bound manual json import lost dispatch origin",
        )

        bound_agv = get_agv_by_id(int(imported_task.preferred_agv_id))
        expect(bound_agv is not None, "bound manual json import preferred AGV missing")
        expect(
            int(bound_agv.x) == 2 and int(bound_agv.y) == 3,
            "bound manual json import did not resolve preferred AGV from dispatch origin",
        )
        expect(str(bound_agv.status) in {"idle", "idle_returning"}, "bound manual json import preferred AGV is not schedulable")

        schedule_data = schedule_service.schedule_task_with_path(
            imported_task.id,
            int(imported_task.preferred_agv_id),
            "manual",
            str(imported_task.dispatch_algorithm or "simple"),
            int(task_items[0].get("grid_cols") or 10),
            int(task_items[0].get("grid_rows") or 8),
            actor=actor,
        )
        expect(schedule_data["task"]["dispatch_mode"] == "manual", "bound manual json import did not schedule in manual mode")
        expect(
            int(schedule_data["task"]["preferred_agv_id"] or 0) == int(imported_task.preferred_agv_id),
            "bound manual json import lost preferred_agv_id during schedule",
        )
        expect(
            int(schedule_data["agv"]["id"]) == int(imported_task.preferred_agv_id),
            "bound manual json import did not bind the preferred AGV",
        )
        expect(schedule_data["path"], "bound manual json import schedule returned an empty path")

        finished_task = wait_for_task_finish(imported_task.id)
        expect(
            finished_task.path_to_start is None and finished_task.path_to_end is None,
            "bound manual json import task retained path fields after finish",
        )


def assert_multi_stage_import() -> None:
    actor = build_actor("json_import_multistage")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.reset_map_layout()
        scoped_agvs = list_agvs()
        expect(len(scoped_agvs) >= 1, "multi-stage json import smoke requires at least one seeded AGV")

        task_ids, task_items = import_demo_tasks("task_multi_stage_demo.json", actor)
        imported_task = get_task_by_id(task_ids[0])
        expect(imported_task is not None, "multi-stage json import task missing after import")
        expect(len(imported_task.stages or []) == len(task_items[0]["stages"]), "multi-stage json import stage count mismatch")
        expect(imported_task.total_stages == len(task_items[0]["stages"]), "multi-stage json import total_stages mismatch")
        expect(str(imported_task.dispatch_mode or "") == "auto", "multi-stage json import dispatch_mode mismatch")

        schedule_data = schedule_service.schedule_task_with_path(
            imported_task.id,
            None,
            "auto",
            str(imported_task.dispatch_algorithm or "simple"),
            int(task_items[0].get("grid_cols") or 10),
            int(task_items[0].get("grid_rows") or 8),
            actor=actor,
        )
        expect(schedule_data["task"]["dispatch_mode"] == "auto", "multi-stage json import did not schedule in auto mode")
        expect(schedule_data["path"], "multi-stage json import schedule returned an empty path")

        finished_task = wait_for_task_finish(imported_task.id, timeout_sec=16.0)
        expect(
            finished_task.current_stage_index == len(task_items[0]["stages"]) - 1,
            "multi-stage json import did not reach the final stage index",
        )
        expect(
            finished_task.path_to_start is None and finished_task.path_to_end is None,
            "multi-stage json import task retained path fields after finish",
        )


def main() -> None:
    cleanup_db_file()
    try:
        summary = initialize_runtime()
        expect(summary["database_status"] == "connected", "task json import smoke sqlite backend did not initialize")

        assert_auto_single_import()
        assert_manual_single_import_waits_for_binding()
        assert_manual_bound_import_origin_resolution()
        assert_multi_stage_import()

        print("TASK_JSON_IMPORT_SMOKE_OK auto_single manual_waiting manual_bound multi_stage")
    finally:
        cleanup_db_file()


if __name__ == "__main__":
    main()
