from __future__ import annotations

import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE_DB_PATH = BACKEND_DIR / "agv_runtime_long_run_smoke.db"
SMOKE_DB_URL = f"sqlite:///{SMOKE_DB_PATH.as_posix()}"

os.environ["AGV_DATA_BACKEND"] = "sqlite"
os.environ["AGV_DATABASE_URL"] = SMOKE_DB_URL
os.environ["AGV_DATABASE_AUTO_CREATE"] = "true"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import dispose_engine  # noqa: E402
from app.core.data_scope import build_scope_key_from_actor, use_scope  # noqa: E402
from app.core.lifecycle import initialize_runtime  # noqa: E402
from app.repositories.agv_repository import get_agv_by_id  # noqa: E402
from app.repositories.task_repository import get_task_by_id  # noqa: E402
from app.schemas.task import TaskCreateRequest  # noqa: E402
from app.services import agv_service, schedule_service, status_service, task_service  # noqa: E402


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


def build_actor(actor_id: str) -> dict[str, str]:
    return {
        "id": actor_id,
        "username": actor_id,
        "role": "personal",
    }


def build_cross_intersection_topology() -> dict:
    return {
        "topology_version": 1,
        "nodes": [
            {"key": "west", "x": 3, "y": 4, "label": "W", "node_type": "station", "capacity": 1},
            {"key": "east", "x": 7, "y": 4, "label": "E", "node_type": "station", "capacity": 1},
            {"key": "north", "x": 5, "y": 2, "label": "N", "node_type": "station", "capacity": 1},
            {"key": "south", "x": 5, "y": 6, "label": "S", "node_type": "station", "capacity": 1},
            {"key": "center", "x": 5, "y": 4, "label": "X", "node_type": "waypoint", "capacity": 1},
        ],
        "edges": [
            {"key": "edge_wx", "source": "west", "target": "center", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
            {"key": "edge_xe", "source": "center", "target": "east", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
            {"key": "edge_nx", "source": "north", "target": "center", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
            {"key": "edge_xs", "source": "center", "target": "south", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
        ],
    }


def create_task(
    actor: dict,
    *,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    priority: int,
) -> int:
    payload = task_service.create_task(
        TaskCreateRequest(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            priority=priority,
        ),
        actor=actor,
    )
    return int(payload["task"]["id"])


def snapshot(agv_ids: list[int], task_ids: list[int]) -> dict:
    agv_samples = []
    for agv_id in agv_ids:
        agv = get_agv_by_id(agv_id)
        expect(agv is not None, f"AGV #{agv_id} disappeared during long-run smoke")
        agv_samples.append(
            {
                "id": int(agv.id),
                "x": int(agv.x),
                "y": int(agv.y),
                "status": str(agv.status),
                "motion_state": str(getattr(agv, "motion_state", "") or ""),
                "current_edge": str(getattr(agv, "current_edge", "") or ""),
                "task_id": int(getattr(agv, "task_id", 0) or 0),
            }
        )

    task_samples = []
    for task_id in task_ids:
        task = get_task_by_id(task_id)
        expect(task is not None, f"task #{task_id} disappeared during long-run smoke")
        task_samples.append(
            {
                "id": int(task.id),
                "status": str(task.status),
                "dispatch_reason": str(getattr(task, "dispatch_reason", "") or ""),
            }
        )

    return {
        "agvs": agv_samples,
        "tasks": task_samples,
    }


def assert_no_duplicate_active_positions(sample: dict) -> None:
    positions: dict[tuple[int, int], int] = {}
    for agv in sample["agvs"]:
        position = (int(agv["x"]), int(agv["y"]))
        previous_agv_id = positions.get(position)
        expect(
            previous_agv_id is None,
            f"AGV #{previous_agv_id} and AGV #{agv['id']} occupied the same grid cell {position}",
        )
        positions[position] = int(agv["id"])


def wait_for_tasks_finish(
    *,
    agv_ids: list[int],
    task_ids: list[int],
    timeout_sec: float = 24.0,
    interval_sec: float = 0.08,
) -> list[dict]:
    samples: list[dict] = []
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        sample = snapshot(agv_ids, task_ids)
        samples.append(sample)
        assert_no_duplicate_active_positions(sample)
        if all(item["status"] == "finished" for item in sample["tasks"]):
            return samples
        time.sleep(interval_sec)
    latest = samples[-1] if samples else {}
    raise AssertionError(f"runtime long-run smoke timed out: {latest}")


def assert_agvs_settled(agv_ids: list[int], *, timeout_sec: float = 3.0) -> None:
    deadline = time.time() + timeout_sec
    latest = {}
    while time.time() < deadline:
        latest = {}
        all_settled = True
        for agv_id in agv_ids:
            agv = get_agv_by_id(agv_id)
            expect(agv is not None, f"AGV #{agv_id} missing after long-run smoke")
            latest[int(agv_id)] = {
                "status": str(agv.status),
                "current_edge": str(getattr(agv, "current_edge", "") or ""),
                "task_id": int(getattr(agv, "task_id", 0) or 0),
            }
            if (
                str(agv.status) != "idle"
                or str(getattr(agv, "current_edge", "") or "").strip()
                or int(getattr(agv, "task_id", 0) or 0) != 0
            ):
                all_settled = False
        if all_settled:
            return
        time.sleep(0.1)
    raise AssertionError(f"AGVs did not settle after long-run round: {latest}")


def assert_cross_intersection_multi_round_runtime() -> None:
    actor = build_actor("runtime_long_cross_intersection")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 11, 9, topology=build_cross_intersection_topology())
        horizontal_agv = agv_service.create_agv(3, 4, actor=actor)["agv"]
        vertical_agv = agv_service.create_agv(5, 2, actor=actor)["agv"]
        agv_ids = [int(horizontal_agv.id), int(vertical_agv.id)]
        observed_wait_or_yield = False

        rounds = [
            ((3, 4), (7, 4), (5, 2), (5, 6)),
            ((7, 4), (3, 4), (5, 6), (5, 2)),
            ((3, 4), (7, 4), (5, 2), (5, 6)),
            ((7, 4), (3, 4), (5, 6), (5, 2)),
        ]

        for index, (h_start, h_end, v_start, v_end) in enumerate(rounds, start=1):
            horizontal_task_id = create_task(
                actor,
                start_x=h_start[0],
                start_y=h_start[1],
                end_x=h_end[0],
                end_y=h_end[1],
                priority=5,
            )
            vertical_task_id = create_task(
                actor,
                start_x=v_start[0],
                start_y=v_start[1],
                end_x=v_end[0],
                end_y=v_end[1],
                priority=4,
            )

            schedule_service.schedule_task_with_path(horizontal_task_id, horizontal_agv.id, "manual", "astar", 11, 9, actor=actor)
            schedule_service.schedule_task_with_path(vertical_task_id, vertical_agv.id, "manual", "astar", 11, 9, actor=actor)

            samples = wait_for_tasks_finish(
                agv_ids=agv_ids,
                task_ids=[horizontal_task_id, vertical_task_id],
            )
            observed_wait_or_yield = observed_wait_or_yield or any(
                agv["motion_state"] in {"waiting", "yielding"}
                for sample in samples
                for agv in sample["agvs"]
            )

            horizontal = get_agv_by_id(horizontal_agv.id)
            vertical = get_agv_by_id(vertical_agv.id)
            expect((int(horizontal.x), int(horizontal.y)) == h_end, f"round {index} horizontal AGV ended at wrong cell")
            expect((int(vertical.x), int(vertical.y)) == v_end, f"round {index} vertical AGV ended at wrong cell")
            assert_agvs_settled(agv_ids)

        expect(observed_wait_or_yield, "cross-intersection long run never exercised waiting/yielding")


def main() -> None:
    cleanup_db_file()
    try:
        summary = initialize_runtime()
        expect(summary["database_status"] == "connected", "runtime long-run smoke sqlite backend did not initialize")
        assert_cross_intersection_multi_round_runtime()
        print("RUNTIME_LONG_RUN_SMOKE_OK cross_intersection_multi_round")
    finally:
        cleanup_db_file()


if __name__ == "__main__":
    main()
