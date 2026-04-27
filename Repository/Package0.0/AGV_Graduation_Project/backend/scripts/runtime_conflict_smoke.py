from __future__ import annotations

import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE_DB_PATH = BACKEND_DIR / "agv_runtime_conflict_smoke.db"
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
from app.utils.agv_movement import _find_grid_yield_path, move_agv  # noqa: E402
from app.utils.task_chain import set_stage_paths  # noqa: E402


BRANCH_EDGE_KEYS = {"edge_ac", "edge_cd", "edge_db"}


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
        "role": "platform_admin",
    }


def build_personal_actor(actor_id: str) -> dict[str, str]:
    return {
        "id": actor_id,
        "username": actor_id,
        "role": "personal",
    }


def build_branch_topology() -> dict:
    return {
        "topology_version": 1,
        "nodes": [
            {"key": "a", "x": 1, "y": 1, "label": "A", "node_type": "station", "capacity": 1},
            {"key": "b", "x": 4, "y": 1, "label": "B", "node_type": "station", "capacity": 1},
            {"key": "c", "x": 1, "y": 2, "label": "C", "node_type": "waypoint", "capacity": 1},
            {"key": "d", "x": 4, "y": 2, "label": "D", "node_type": "waypoint", "capacity": 1},
        ],
        "edges": [
            {"key": "edge_ab", "source": "a", "target": "b", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
            {"key": "edge_ac", "source": "a", "target": "c", "direction": "bidirectional", "lane_type": "branch", "speed_multiplier": 1.0},
            {"key": "edge_cd", "source": "c", "target": "d", "direction": "bidirectional", "lane_type": "branch", "speed_multiplier": 1.0},
            {"key": "edge_db", "source": "d", "target": "b", "direction": "bidirectional", "lane_type": "branch", "speed_multiplier": 1.0},
        ],
    }


def build_follow_topology() -> dict:
    return {
        "topology_version": 1,
        "nodes": [
            {"key": "a", "x": 1, "y": 1, "label": "A", "node_type": "station", "capacity": 1},
            {"key": "b", "x": 8, "y": 1, "label": "B", "node_type": "station", "capacity": 1},
        ],
        "edges": [
            {"key": "edge_ab", "source": "a", "target": "b", "direction": "bidirectional", "lane_type": "main", "speed_multiplier": 1.0},
        ],
    }


def path_uses_branch(path: list[dict]) -> bool:
    for point in path or []:
        if int(point.get("y", -1)) == 2:
            return True
        if str(point.get("topology_edge_key") or "").strip() in BRANCH_EDGE_KEYS:
            return True
    return False


def snapshot_pair(left_agv_id: int, right_agv_id: int, left_task_id: int, right_task_id: int) -> dict:
    left_agv = get_agv_by_id(left_agv_id)
    right_agv = get_agv_by_id(right_agv_id)
    left_task = get_task_by_id(left_task_id)
    right_task = get_task_by_id(right_task_id)
    return {
        "left": {
            "x": int(left_agv.x),
            "y": int(left_agv.y),
            "status": str(left_agv.status),
            "motion_state": str(getattr(left_agv, "motion_state", "") or ""),
            "current_edge": str(getattr(left_agv, "current_edge", "") or ""),
        },
        "right": {
            "x": int(right_agv.x),
            "y": int(right_agv.y),
            "status": str(right_agv.status),
            "motion_state": str(getattr(right_agv, "motion_state", "") or ""),
            "current_edge": str(getattr(right_agv, "current_edge", "") or ""),
        },
        "left_task": {
            "status": str(left_task.status),
            "dispatch_reason": str(getattr(left_task, "dispatch_reason", "") or ""),
        },
        "right_task": {
            "status": str(right_task.status),
            "dispatch_reason": str(getattr(right_task, "dispatch_reason", "") or ""),
        },
    }


def active_motion_segment_key(agv) -> tuple[tuple[int, int], tuple[int, int]] | None:
    if not getattr(agv, "motion_started_at", None) or int(getattr(agv, "motion_duration_ms", 0) or 0) <= 0:
        return None
    source = (
        int(round(float(getattr(agv, "motion_source_x", agv.x) or agv.x))),
        int(round(float(getattr(agv, "motion_source_y", agv.y) or agv.y))),
    )
    target = (
        int(round(float(getattr(agv, "motion_target_x", agv.x) or agv.x))),
        int(round(float(getattr(agv, "motion_target_y", agv.y) or agv.y))),
    )
    if source == target:
        return None
    return tuple(sorted((source, target)))


def wait_for_pair_finish(
    left_agv_id: int,
    right_agv_id: int,
    left_task_id: int,
    right_task_id: int,
    *,
    timeout_sec: float = 18.0,
    interval_sec: float = 0.1,
) -> list[dict]:
    samples: list[dict] = []
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        sample = snapshot_pair(left_agv_id, right_agv_id, left_task_id, right_task_id)
        samples.append(sample)
        if sample["left_task"]["status"] == "finished" and sample["right_task"]["status"] == "finished":
            return samples
        time.sleep(interval_sec)
    raise AssertionError(
        f"runtime conflict smoke timed out: left={get_task_by_id(left_task_id).status} right={get_task_by_id(right_task_id).status}"
    )


def wait_for_personal_grid_pair_finish(
    left_agv_id: int,
    right_agv_id: int,
    left_task_id: int,
    right_task_id: int,
    *,
    timeout_sec: float = 24.0,
    interval_sec: float = 0.08,
) -> dict[str, bool]:
    observed_grid_replan = False
    observed_grid_yield = False
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        left_agv = get_agv_by_id(left_agv_id)
        right_agv = get_agv_by_id(right_agv_id)
        left_task = get_task_by_id(left_task_id)
        right_task = get_task_by_id(right_task_id)

        expect((int(left_agv.x), int(left_agv.y)) != (int(right_agv.x), int(right_agv.y)), "personal grid AGVs occupied the same cell")
        left_segment = active_motion_segment_key(left_agv)
        right_segment = active_motion_segment_key(right_agv)
        if left_segment is not None and right_segment is not None:
            expect(left_segment != right_segment, f"personal grid AGVs used the same motion segment {left_segment}")

        observed_grid_replan = observed_grid_replan or any(
            str(getattr(task, "dispatch_reason", "") or "").startswith("grid_dynamic_replan")
            for task in (left_task, right_task)
        )
        observed_grid_yield = observed_grid_yield or any(
            str(getattr(task, "dispatch_reason", "") or "").startswith("grid_dynamic_yield")
            for task in (left_task, right_task)
        )
        if left_task.status == "finished" and right_task.status == "finished":
            return {"replan": observed_grid_replan, "yield": observed_grid_yield}
        time.sleep(interval_sec)
    raise AssertionError(
        f"personal grid head-on smoke timed out: left={get_task_by_id(left_task_id).status} right={get_task_by_id(right_task_id).status}"
    )


def assert_no_simultaneous_edge_usage(samples: list[dict], edge_key: str, message: str) -> None:
    expect(
        not any(
            sample["left"]["current_edge"] == edge_key and sample["right"]["current_edge"] == edge_key
            for sample in samples
        ),
        message,
    )


def assert_finished_pair(left_task_id: int, right_task_id: int, message_prefix: str) -> None:
    expect(get_task_by_id(left_task_id).status == "finished", f"{message_prefix}: left task did not finish")
    expect(get_task_by_id(right_task_id).status == "finished", f"{message_prefix}: right task did not finish")


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


def assert_same_corridor_follow_runtime() -> None:
    actor = build_actor("runtime_follow_conflict")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=build_follow_topology())
        lead_agv = agv_service.create_agv(2, 1, actor=actor)["agv"]
        follower_agv = agv_service.create_agv(1, 1, actor=actor)["agv"]
        lead_task_id = create_task(actor, start_x=2, start_y=1, end_x=8, end_y=1, priority=5)
        follower_task_id = create_task(actor, start_x=1, start_y=1, end_x=8, end_y=1, priority=3)

        schedule_service.schedule_task_with_path(lead_task_id, lead_agv.id, "manual", "astar", 10, 8, actor=actor)
        time.sleep(0.15)
        schedule_service.schedule_task_with_path(follower_task_id, follower_agv.id, "manual", "astar", 10, 8, actor=actor)

        samples = wait_for_pair_finish(lead_agv.id, follower_agv.id, lead_task_id, follower_task_id)
        assert_finished_pair(lead_task_id, follower_task_id, "follow runtime")
        assert_no_simultaneous_edge_usage(samples, "edge_ab", "follower entered the same corridor edge while the leader still occupied it")
        expect(
            any(sample["right"]["motion_state"] in {"waiting", "yielding"} for sample in samples),
            "follower never entered waiting/yielding during same-corridor follow runtime",
        )


def assert_headon_planner_priority_reroute() -> None:
    actor = build_actor("runtime_headon_priority_plan")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=build_branch_topology())
        left_agv = agv_service.create_agv(1, 1, actor=actor)["agv"]
        right_agv = agv_service.create_agv(4, 1, actor=actor)["agv"]
        left_task_id = create_task(actor, start_x=1, start_y=1, end_x=4, end_y=1, priority=5)
        right_task_id = create_task(actor, start_x=4, start_y=1, end_x=1, end_y=1, priority=2)

        schedule_service.schedule_task_with_path(left_task_id, left_agv.id, "manual", "astar", 10, 8, actor=actor)
        time.sleep(0.15)
        right_schedule = schedule_service.schedule_task_with_path(right_task_id, right_agv.id, "manual", "astar", 10, 8, actor=actor)

        expect(path_uses_branch(right_schedule["path"]), "low-priority head-on task did not choose the branch path during planning")
        samples = wait_for_pair_finish(left_agv.id, right_agv.id, left_task_id, right_task_id)
        assert_finished_pair(left_task_id, right_task_id, "head-on priority planning")
        assert_no_simultaneous_edge_usage(samples, "edge_ab", "planner priority reroute still allowed simultaneous occupancy on the main edge")


def assert_headon_planner_deadlock_tiebreak() -> None:
    actor = build_actor("runtime_headon_deadlock_plan")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=build_branch_topology())
        older_agv = agv_service.create_agv(1, 1, actor=actor)["agv"]
        newer_agv = agv_service.create_agv(4, 1, actor=actor)["agv"]
        older_task_id = create_task(actor, start_x=1, start_y=1, end_x=4, end_y=1, priority=3)
        newer_task_id = create_task(actor, start_x=4, start_y=1, end_x=1, end_y=1, priority=3)
        get_task_by_id(older_task_id).created_at = "2026-04-12T10:02:00"
        get_task_by_id(newer_task_id).created_at = "2026-04-12T10:02:05"

        schedule_service.schedule_task_with_path(older_task_id, older_agv.id, "manual", "astar", 10, 8, actor=actor)
        time.sleep(0.15)
        newer_schedule = schedule_service.schedule_task_with_path(newer_task_id, newer_agv.id, "manual", "astar", 10, 8, actor=actor)

        expect(path_uses_branch(newer_schedule["path"]), "newer same-priority head-on task did not take the branch path during tie-break planning")
        samples = wait_for_pair_finish(older_agv.id, newer_agv.id, older_task_id, newer_task_id)
        assert_finished_pair(older_task_id, newer_task_id, "head-on deadlock tie-break planning")
        assert_no_simultaneous_edge_usage(samples, "edge_ab", "deadlock tie-break planning still allowed simultaneous occupancy on the main edge")


def assert_concurrent_edge_claim_runtime() -> None:
    actor = build_actor("runtime_concurrent_claim")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=build_branch_topology())
        left_agv = agv_service.create_agv(1, 1, actor=actor)["agv"]
        right_agv = agv_service.create_agv(4, 1, actor=actor)["agv"]
        left_task_id = create_task(actor, start_x=1, start_y=1, end_x=4, end_y=1, priority=5)
        right_task_id = create_task(actor, start_x=4, start_y=1, end_x=1, end_y=1, priority=2)
        left_task = get_task_by_id(left_task_id)
        right_task = get_task_by_id(right_task_id)

        for agv, task in ((left_agv, left_task), (right_agv, right_task)):
            task.status = "running"
            task.agv_id = agv.id
            agv.status = "running"
            agv.task_id = task.id
            agv.clear_motion(motion_state="running")

        set_stage_paths(left_task, [{"x": 1, "y": 1}], [{"x": 1, "y": 1}, {"x": 4, "y": 1, "topology_edge_key": "edge_ab"}])
        set_stage_paths(right_task, [{"x": 4, "y": 1}], [{"x": 4, "y": 1}, {"x": 1, "y": 1, "topology_edge_key": "edge_ab"}])

        move_agv(left_agv.id, left_task.id, "astar", 10, 8)
        move_agv(right_agv.id, right_task.id, "astar", 10, 8)

        samples = wait_for_pair_finish(left_agv.id, right_agv.id, left_task_id, right_task_id)
        assert_finished_pair(left_task_id, right_task_id, "concurrent claim runtime")
        assert_no_simultaneous_edge_usage(samples, "edge_ab", "concurrent runtime start still allowed both AGVs to claim the same main edge")
        expect(
            any(
                sample["left"]["motion_state"] in {"waiting", "yielding"}
                or sample["right"]["motion_state"] in {"waiting", "yielding"}
                for sample in samples
            ),
            "concurrent runtime start never entered waiting/yielding despite shared edge pressure",
        )


def assert_personal_grid_headon_dynamic_reroute() -> None:
    actor = build_personal_actor("runtime_personal_grid_headon")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=None, force_apply=True, actor=actor)
        left_agv = agv_service.create_agv(1, 2, actor=actor)["agv"]
        right_agv = agv_service.create_agv(5, 2, actor=actor)["agv"]
        left_task_id = create_task(actor, start_x=1, start_y=2, end_x=5, end_y=2, priority=8)
        right_task_id = create_task(actor, start_x=5, start_y=2, end_x=1, end_y=2, priority=4)

        schedule_service.schedule_task_with_path(left_task_id, left_agv.id, "manual", "astar", 10, 8, actor=actor)
        time.sleep(0.12)
        schedule_service.schedule_task_with_path(right_task_id, right_agv.id, "manual", "astar", 10, 8, actor=actor)

        avoidance_observations = wait_for_personal_grid_pair_finish(
            left_agv.id,
            right_agv.id,
            left_task_id,
            right_task_id,
        )
        assert_finished_pair(left_task_id, right_task_id, "personal grid head-on")
        expect(
            avoidance_observations["replan"] or avoidance_observations["yield"],
            "personal grid head-on runtime never triggered dynamic avoidance",
        )
        expect(avoidance_observations["yield"], "personal grid head-on runtime never triggered a yield maneuver")


def assert_personal_grid_yield_path_clears_corridor() -> None:
    actor = build_personal_actor("runtime_personal_grid_yield_path")
    scope_key = build_scope_key_from_actor(actor)
    with use_scope(scope_key):
        status_service.update_map_layout([], None, 10, 8, topology=None, force_apply=True, actor=actor)
        yielding_agv = agv_service.create_agv(8, 3, actor=actor)["agv"]
        blocker_agv = agv_service.create_agv(7, 3, actor=actor)["agv"]

        yield_path = _find_grid_yield_path(yielding_agv, blocker_agv, 7, 3, 10, 8)
        expect(len(yield_path) >= 3, "personal grid yield path did not leave the corridor deeply enough")
        final_point = yield_path[-1]
        expect(
            abs(int(final_point["y"]) - int(yielding_agv.y)) >= 2,
            f"personal grid yield target still stayed too close to the conflict corridor: {final_point}",
        )


def main() -> None:
    cleanup_db_file()
    try:
        summary = initialize_runtime()
        expect(summary["database_status"] == "connected", "runtime conflict smoke sqlite backend did not initialize")

        assert_same_corridor_follow_runtime()
        assert_headon_planner_priority_reroute()
        assert_headon_planner_deadlock_tiebreak()
        assert_concurrent_edge_claim_runtime()
        assert_personal_grid_headon_dynamic_reroute()
        assert_personal_grid_yield_path_clears_corridor()

        print("RUNTIME_CONFLICT_SMOKE_OK follow_runtime planner_priority planner_deadlock concurrent_claim personal_grid_headon personal_grid_yield_path")
    finally:
        cleanup_db_file()


if __name__ == "__main__":
    main()
