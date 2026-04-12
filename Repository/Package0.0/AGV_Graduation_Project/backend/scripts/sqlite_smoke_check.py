from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from sqlalchemy import select


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE_DB_PATH = BACKEND_DIR / "agv_dispatch_smoke.db"
SMOKE_DB_URL = f"sqlite:///{SMOKE_DB_PATH.as_posix()}"

os.environ["AGV_DATA_BACKEND"] = "sqlite"
os.environ["AGV_DATABASE_URL"] = SMOKE_DB_URL
os.environ["AGV_DATABASE_AUTO_CREATE"] = "true"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import dispose_engine, get_db_session  # noqa: E402
from app.core.data_scope import build_scope_key_from_actor, build_scoped_storage_id, use_scope  # noqa: E402
from app.core.lifecycle import initialize_runtime  # noqa: E402
from app.repositories.agv_repository import list_agvs  # noqa: E402
from app.repositories.task_repository import get_task_by_id  # noqa: E402
from app.repositories.sql_models import AgvEntity, MapLayoutEntity, PointLibraryEntity, TaskTemplateEntity, UiSettingsEntity  # noqa: E402
from app.schemas.point import PointUpsertRequest  # noqa: E402
from app.schemas.status import BlockedCellPayload, UiSettingsUpdateRequest  # noqa: E402
from app.schemas.task import TaskCreateRequest  # noqa: E402
from app.schemas.template import TaskTemplateStagePayload, TaskTemplateUpsertRequest  # noqa: E402
from app.services import agv_service, point_service, schedule_service, status_service, task_service, template_service  # noqa: E402
from app.utils.path_planner import build_runtime_special_node_constraints  # noqa: E402
from app.utils.task_chain import set_stage_paths  # noqa: E402


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def cleanup_db_file() -> None:
    try:
        dispose_engine()
    except Exception:
        pass
    if SMOKE_DB_PATH.exists():
        SMOKE_DB_PATH.unlink()


def blocked_cells_to_set(items: list[dict]) -> set[tuple[int, int]]:
    return {(int(item["x"]), int(item["y"])) for item in items}


def assert_scope_isolation() -> None:
    personal_actor = {
        "id": "smoke_personal",
        "username": "smoke_personal",
        "role": "personal",
    }
    enterprise_admin_actor = {
        "id": "smoke_enterprise_admin",
        "username": "smoke_enterprise_admin",
        "role": "enterprise_admin",
        "organization_id": "smoke_enterprise",
        "organization_name": "Smoke Enterprise",
    }
    enterprise_operator_actor = {
        "id": "smoke_enterprise_operator",
        "username": "smoke_enterprise_operator",
        "role": "enterprise_operator",
        "organization_id": "smoke_enterprise",
        "organization_name": "Smoke Enterprise",
    }
    enterprise_logistics_actor = {
        "id": "smoke_enterprise_logistics",
        "username": "smoke_enterprise_logistics",
        "role": "enterprise_logistics",
        "organization_id": "smoke_enterprise",
        "organization_name": "Smoke Enterprise",
    }
    platform_actor = {
        "id": "smoke_platform_admin",
        "username": "smoke_platform_admin",
        "role": "platform_admin",
    }
    personal_scope = build_scope_key_from_actor(personal_actor)
    enterprise_scope = build_scope_key_from_actor(enterprise_admin_actor)
    enterprise_operator_scope = build_scope_key_from_actor(enterprise_operator_actor)
    enterprise_logistics_scope = build_scope_key_from_actor(enterprise_logistics_actor)
    platform_scope = build_scope_key_from_actor(platform_actor)
    expect(personal_scope == "user:smoke_personal", "personal actor scope key mismatch")
    expect(enterprise_scope == "organization:smoke_enterprise", "enterprise admin scope key mismatch")
    expect(enterprise_operator_scope == enterprise_scope, "enterprise operator should share organization scope")
    expect(enterprise_logistics_scope == enterprise_scope, "enterprise logistics should share organization scope")
    expect(personal_scope != enterprise_scope, "personal scope must remain isolated from enterprise scope")
    expect(platform_scope != enterprise_scope, "platform scope must remain isolated from enterprise scope")

    shared_point_id = "scope_shared_point"
    shared_template_id = "scope_shared_template"
    personal_node_key = "scope-personal-node"
    enterprise_node_key = "scope-enterprise-node"
    logistics_shared_point_id = "scope_enterprise_logistics_point"
    logistics_shared_template_id = "scope_enterprise_logistics_template"
    personal_agv_id = None
    enterprise_agv_id = None

    with use_scope(personal_scope):
        point_service.create_or_update_point(
            PointUpsertRequest(
                id=shared_point_id,
                x=1,
                y=1,
                name_key=None,
                zone_key="personal_zone",
                custom_name="Personal Scope Point",
                aliases=["personal"],
                custom=True,
            )
        )
        template_service.create_or_update_template(
            TaskTemplateUpsertRequest(
                id=shared_template_id,
                priority=2,
                name_key=None,
                custom_name="Personal Scope Template",
                custom=True,
                stages=[
                    TaskTemplateStagePayload(index=0, start_x=0, start_y=0, end_x=1, end_y=1, label="personal"),
                ],
            )
        )
        personal_map = status_service.update_map_layout(
            [BlockedCellPayload(x=9, y=0)],
            None,
            10,
            8,
            topology={
                "topology_version": 1,
                "nodes": [
                    {
                        "key": personal_node_key,
                        "x": 1,
                        "y": 1,
                        "label": "Personal Scope Node",
                        "node_type": "parking",
                        "capacity": 2,
                    }
                ],
                "edges": [],
            },
        )
        expect(
            any(point["id"] == shared_point_id for point in point_service.get_point_list()),
            "personal scope point missing after save",
        )
        expect(
            any(template["id"] == shared_template_id for template in template_service.get_template_list()),
            "personal scope template missing after save",
        )
        expect(
            any(node["key"] == personal_node_key for node in personal_map["topology"]["nodes"]),
            "personal scope topology node missing after save",
        )
        personal_create_result = agv_service.create_agv(2, 6, actor=personal_actor)
        personal_agv_id = int(personal_create_result["agv"].id)
        expect(
            any(
                int(agv.id) == personal_agv_id and int(agv.x) == 2 and int(agv.y) == 6
                for agv in list_agvs()
            ),
            "personal scope agv missing after save",
        )

    with use_scope(enterprise_scope):
        enterprise_points_before = point_service.get_point_list()
        enterprise_templates_before = template_service.get_template_list()
        enterprise_map_before = status_service.get_map_layout()
        expect(
            not any(point["id"] == shared_point_id for point in enterprise_points_before),
            "personal scope point leaked into enterprise scope",
        )
        expect(
            not any(template["id"] == shared_template_id for template in enterprise_templates_before),
            "personal scope template leaked into enterprise scope",
        )
        expect(
            not any(node["key"] == personal_node_key for node in enterprise_map_before["topology"]["nodes"]),
            "personal scope topology leaked into enterprise scope",
        )
        expect(
            not any(int(agv.id) == personal_agv_id for agv in list_agvs()),
            "personal scope AGV leaked into enterprise scope",
        )

        point_service.create_or_update_point(
            PointUpsertRequest(
                id=shared_point_id,
                x=8,
                y=7,
                name_key=None,
                zone_key="enterprise_zone",
                custom_name="Enterprise Scope Point",
                aliases=["enterprise"],
                custom=True,
            )
        )
        template_service.create_or_update_template(
            TaskTemplateUpsertRequest(
                id=shared_template_id,
                priority=5,
                name_key=None,
                custom_name="Enterprise Scope Template",
                custom=True,
                stages=[
                    TaskTemplateStagePayload(index=0, start_x=8, start_y=7, end_x=9, end_y=7, label="enterprise"),
                ],
            )
        )
        enterprise_map = status_service.update_map_layout(
            [BlockedCellPayload(x=0, y=7)],
            None,
            10,
            8,
            topology={
                "topology_version": 1,
                "nodes": [
                    {
                        "key": enterprise_node_key,
                        "x": 8,
                        "y": 7,
                        "label": "Enterprise Scope Node",
                        "node_type": "charge",
                        "capacity": 3,
                    }
                ],
                "edges": [],
            },
        )
        expect(
            blocked_cells_to_set(enterprise_map["blocked_cells"]) == {(0, 7)},
            "enterprise scope blocked cells mismatch",
        )
        expect(
            any(node["key"] == enterprise_node_key for node in enterprise_map["topology"]["nodes"]),
            "enterprise scope topology node missing after save",
        )
        enterprise_points_after = point_service.get_point_list()
        enterprise_templates_after = template_service.get_template_list()
        expect(
            any(point["id"] == shared_point_id and int(point["x"]) == 8 and int(point["y"]) == 7 for point in enterprise_points_after),
            "enterprise scope point missing after save",
        )
        expect(
            any(
                template["id"] == shared_template_id
                and int(template["priority"]) == 5
                and int(template["stages"][0]["start_x"]) == 8
                and int(template["stages"][0]["start_y"]) == 7
                for template in enterprise_templates_after
            ),
            "enterprise scope template missing after save",
        )
        enterprise_create_result = agv_service.create_agv(None, None, point_id=enterprise_node_key, actor=enterprise_admin_actor)
        enterprise_agv_id = int(enterprise_create_result["agv"].id)
        expect(
            any(
                int(agv.id) == enterprise_agv_id and str(getattr(agv, "current_node", "") or "").strip() == enterprise_node_key
                for agv in list_agvs()
            ),
            "enterprise scope AGV missing after save",
        )

    with use_scope(enterprise_operator_scope):
        operator_points = point_service.get_point_list()
        operator_templates = template_service.get_template_list()
        operator_map = status_service.get_map_layout()
        operator_agvs = list_agvs()
        expect(
            any(point["id"] == shared_point_id and int(point["x"]) == 8 and int(point["y"]) == 7 for point in operator_points),
            "enterprise admin point not visible to operator in same organization",
        )
        expect(
            any(template["id"] == shared_template_id and int(template["priority"]) == 5 for template in operator_templates),
            "enterprise admin template not visible to operator in same organization",
        )
        expect(
            any(node["key"] == enterprise_node_key for node in operator_map["topology"]["nodes"]),
            "enterprise admin topology not visible to operator in same organization",
        )
        expect(
            any(int(agv.id) == enterprise_agv_id for agv in operator_agvs),
            "enterprise admin AGV not visible to operator in same organization",
        )

    with use_scope(enterprise_logistics_scope):
        point_service.create_or_update_point(
            PointUpsertRequest(
                id=logistics_shared_point_id,
                x=7,
                y=6,
                name_key=None,
                zone_key="enterprise_zone",
                custom_name="Enterprise Logistics Point",
                aliases=["enterprise", "logistics"],
                custom=True,
            )
        )
        template_service.create_or_update_template(
            TaskTemplateUpsertRequest(
                id=logistics_shared_template_id,
                priority=6,
                name_key=None,
                custom_name="Enterprise Logistics Template",
                custom=True,
                stages=[
                    TaskTemplateStagePayload(index=0, start_x=7, start_y=6, end_x=8, end_y=6, label="logistics"),
                ],
            )
        )
        expect(
            any(point["id"] == logistics_shared_point_id for point in point_service.get_point_list()),
            "enterprise logistics point missing after same-scope save",
        )
        expect(
            any(template["id"] == logistics_shared_template_id for template in template_service.get_template_list()),
            "enterprise logistics template missing after same-scope save",
        )

    with use_scope(personal_scope):
        personal_points_after = point_service.get_point_list()
        personal_templates_after = template_service.get_template_list()
        personal_map_after = status_service.get_map_layout()
        personal_agvs_after = list_agvs()
        expect(
            any(point["id"] == shared_point_id and int(point["x"]) == 1 and int(point["y"]) == 1 for point in personal_points_after),
            "personal scope point lost after enterprise write",
        )
        expect(
            any(
                template["id"] == shared_template_id
                and int(template["priority"]) == 2
                and int(template["stages"][0]["start_x"]) == 0
                and int(template["stages"][0]["start_y"]) == 0
                for template in personal_templates_after
            ),
            "personal scope template lost after enterprise write",
        )
        expect(
            any(node["key"] == personal_node_key for node in personal_map_after["topology"]["nodes"]),
            "personal scope topology node lost after enterprise write",
        )
        expect(
            not any(node["key"] == enterprise_node_key for node in personal_map_after["topology"]["nodes"]),
            "enterprise scope topology leaked back into personal scope",
        )
        expect(
            not any(point["id"] == logistics_shared_point_id for point in personal_points_after),
            "enterprise logistics point leaked into personal scope",
        )
        expect(
            not any(template["id"] == logistics_shared_template_id for template in personal_templates_after),
            "enterprise logistics template leaked into personal scope",
        )
        expect(
            any(int(agv.id) == personal_agv_id for agv in personal_agvs_after),
            "personal scope AGV lost after enterprise write",
        )
        expect(
            not any(int(agv.id) == enterprise_agv_id for agv in personal_agvs_after),
            "enterprise scope AGV leaked back into personal scope",
        )

    with use_scope(enterprise_scope):
        enterprise_points_final = point_service.get_point_list()
        enterprise_templates_final = template_service.get_template_list()
        enterprise_agvs_final = list_agvs()
        expect(
            any(point["id"] == logistics_shared_point_id and int(point["x"]) == 7 and int(point["y"]) == 6 for point in enterprise_points_final),
            "enterprise logistics point not visible to admin in same organization",
        )
        expect(
            any(template["id"] == logistics_shared_template_id and int(template["priority"]) == 6 for template in enterprise_templates_final),
            "enterprise logistics template not visible to admin in same organization",
        )
        expect(
            any(int(agv.id) == enterprise_agv_id for agv in enterprise_agvs_final),
            "enterprise AGV missing after same-organization role round trip",
        )

    with get_db_session() as session:
        point_ids = {
            build_scoped_storage_id(shared_point_id, personal_scope),
            build_scoped_storage_id(shared_point_id, enterprise_scope),
        }
        stored_points = {
            entity.id for entity in session.execute(select(PointLibraryEntity).where(PointLibraryEntity.id.in_(point_ids))).scalars().all()
        }
        expect(
            build_scoped_storage_id(shared_point_id, personal_scope) in stored_points,
            "personal scoped point row missing in sqlite db",
        )
        expect(
            build_scoped_storage_id(shared_point_id, enterprise_scope) in stored_points,
            "enterprise scoped point row missing in sqlite db",
        )

        template_ids = {
            build_scoped_storage_id(shared_template_id, personal_scope),
            build_scoped_storage_id(shared_template_id, enterprise_scope),
        }
        stored_templates = {
            entity.id for entity in session.execute(select(TaskTemplateEntity).where(TaskTemplateEntity.id.in_(template_ids))).scalars().all()
        }
        expect(
            build_scoped_storage_id(shared_template_id, personal_scope) in stored_templates,
            "personal scoped template row missing in sqlite db",
        )
        expect(
            build_scoped_storage_id(shared_template_id, enterprise_scope) in stored_templates,
            "enterprise scoped template row missing in sqlite db",
        )

        stored_layout_scopes = {
            str(entity.scope_key or "")
            for entity in session.execute(
                select(MapLayoutEntity).where(MapLayoutEntity.scope_key.in_([personal_scope, enterprise_scope]))
            ).scalars().all()
        }
        expect(personal_scope in stored_layout_scopes, "personal scope map row missing in sqlite db")
        expect(enterprise_scope in stored_layout_scopes, "enterprise scope map row missing in sqlite db")

        stored_agvs = {
            (int(entity.id), str(entity.scope_key or ""))
            for entity in session.execute(
                select(AgvEntity).where(AgvEntity.scope_key.in_([personal_scope, enterprise_scope]))
            ).scalars().all()
        }
        expect(
            (int(personal_agv_id), personal_scope) in stored_agvs,
            "personal scoped agv row missing in sqlite db",
        )
        expect(
            (int(enterprise_agv_id), enterprise_scope) in stored_agvs,
            "enterprise scoped agv row missing in sqlite db",
        )


def assert_reserved_special_node_constraints() -> None:
    charge_scope = "organization:smoke_reserved_charge"
    charge_a_key = "charge_reserved_a"
    charge_b_key = "charge_reserved_b"

    with use_scope(charge_scope):
        status_service.update_map_layout(
            [],
            None,
            10,
            8,
            topology={
                "topology_version": 1,
                "nodes": [
                    {
                        "key": charge_a_key,
                        "x": 4,
                        "y": 1,
                        "label": "Reserved Charge A",
                        "node_type": "charge",
                        "capacity": 4,
                    },
                    {
                        "key": charge_b_key,
                        "x": 4,
                        "y": 2,
                        "label": "Reserved Charge B",
                        "node_type": "charge",
                        "capacity": 4,
                    },
                ],
                "edges": [],
            },
        )

        agv_service.create_agv(0, 0)
        agv_service.create_agv(0, 1)

        scoped_agvs = list_agvs()
        expect(len(scoped_agvs) >= 5, "reserved special-node smoke scenario needs at least 5 AGVs")

        reserving_agvs = scoped_agvs[:4]
        probing_agv = scoped_agvs[4]

        for agv in reserving_agvs:
            agv.status = "waiting_for_charge"
            agv.auto_target_node = charge_a_key
            agv.auto_target_type = "charge"
            agv.current_node = str(getattr(agv, "current_node", "") or f"grid:{int(agv.x)}:{int(agv.y)}")
            agv.clear_motion(motion_state="waiting")

        probing_agv.status = "idle"
        probing_agv.auto_target_node = None
        probing_agv.auto_target_type = None
        probing_agv.current_node = str(getattr(probing_agv, "current_node", "") or f"grid:{int(probing_agv.x)}:{int(probing_agv.y)}")
        probing_agv.clear_motion()

        constraints = build_runtime_special_node_constraints(
            exclude_agv_id=probing_agv.id,
            goal_node_key=charge_b_key,
            allowed_node_keys={charge_b_key},
        )
        expect(
            (4, 1) in set(constraints["blocked_positions"]),
            "reserved charge node was not blocked after capacity was fully reserved",
        )
        expect(
            charge_a_key in set(constraints["avoid_node_keys"]),
            "reserved charge node key missing from runtime avoidance constraints",
        )


def assert_ui_settings_roundtrip() -> None:
    initial_settings = status_service.get_ui_settings()
    expect(
        "idle_charge_battery_threshold" in initial_settings,
        "ui settings payload missing idle charge battery threshold",
    )
    expect(
        "low_battery_threshold" in initial_settings,
        "ui settings payload missing low battery threshold",
    )

    updated_settings = status_service.update_ui_settings(
        UiSettingsUpdateRequest(
            **{
                **initial_settings,
                "data_backend": None,
                "idle_charge_timeout_sec": 52.0,
                "idle_charge_battery_threshold": 58.0,
                "low_battery_threshold": 26.0,
            }
        )
    )
    expect(
        float(updated_settings["idle_charge_timeout_sec"]) == 52.0,
        "updated idle charge timeout was not persisted",
    )
    expect(
        float(updated_settings["idle_charge_battery_threshold"]) == 58.0,
        "updated idle charge battery threshold was not persisted",
    )
    expect(
        float(updated_settings["low_battery_threshold"]) == 26.0,
        "updated low battery threshold was not persisted",
    )

    with get_db_session() as session:
        ui_entity = session.execute(select(UiSettingsEntity).order_by(UiSettingsEntity.id.desc())).scalars().first()
        expect(ui_entity is not None, "ui settings row missing in sqlite db")
        expect(
            float(ui_entity.idle_charge_battery_threshold) == 58.0,
            "sqlite ui settings row missing idle charge battery threshold update",
        )
        expect(
            float(ui_entity.low_battery_threshold) == 26.0,
            "sqlite ui settings row missing low battery threshold update",
        )


def assert_task_path_lifecycle() -> None:
    actor = {
        "id": "smoke_task_operator",
        "username": "smoke_task_operator",
        "role": "personal",
    }
    task_scope = build_scope_key_from_actor(actor)

    with use_scope(task_scope):
        status_service.reset_map_layout()

        auto_agv = agv_service.create_agv(1, 1, actor=actor)["agv"]
        auto_task_id = int(
            task_service.create_task(
                TaskCreateRequest(
                    start_x=1,
                    start_y=1,
                    end_x=2,
                    end_y=1,
                    priority=2,
                ),
                actor=actor,
            )["task"]["id"]
        )
        auto_schedule = schedule_service.schedule_task_with_path(
            auto_task_id,
            auto_agv.id,
            "manual",
            "simple",
            10,
            8,
            actor=actor,
        )
        expect(auto_schedule["path_to_start"], "scheduled task payload missing path_to_start")
        expect(auto_schedule["path_to_end"], "scheduled task payload missing path_to_end")
        expect(auto_schedule["task"]["path_to_start"], "scheduled task snapshot missing immediate path_to_start")
        expect(auto_schedule["task"]["path_to_end"], "scheduled task snapshot missing immediate path_to_end")

        auto_task = get_task_by_id(auto_task_id)
        expect(auto_task is not None, "scheduled auto-finish task not found")
        expect(auto_task.path_to_start is not None, "scheduled auto-finish task did not persist path_to_start")
        expect(auto_task.path_to_end is not None, "scheduled auto-finish task did not persist path_to_end")

        auto_deadline = time.time() + 8.0
        while time.time() < auto_deadline:
            auto_task = get_task_by_id(auto_task_id)
            if auto_task is not None and auto_task.status == "finished":
                break
            time.sleep(0.1)

        expect(auto_task is not None and auto_task.status == "finished", "auto-finish task did not reach finished state")
        expect(auto_task.path_to_start is None, "auto-finish task retained path_to_start after completion")
        expect(auto_task.path_to_end is None, "auto-finish task retained path_to_end after completion")
        expect(auto_task.path_length_to_start is None, "auto-finish task retained path_length_to_start after completion")
        expect(auto_task.path_length_to_end is None, "auto-finish task retained path_length_to_end after completion")

        auto_agv_runtime = next((item for item in list_agvs() if int(item.id) == int(auto_agv.id)), None)
        expect(auto_agv_runtime is not None, "auto-finish AGV missing after completion")
        expect(auto_agv_runtime.status == "idle", "auto-finish AGV did not return to idle")
        expect(auto_agv_runtime.task_id is None, "auto-finish AGV still bound to finished task")

        manual_agv = agv_service.create_agv(1, 3, actor=actor)["agv"]
        manual_task_id = int(
            task_service.create_task(
                TaskCreateRequest(
                    start_x=1,
                    start_y=3,
                    end_x=8,
                    end_y=3,
                    priority=3,
                ),
                actor=actor,
            )["task"]["id"]
        )
        manual_task = get_task_by_id(manual_task_id)
        expect(manual_task is not None, "manual-finish task not found after create")

        manual_task.status = "running"
        manual_task.agv_id = manual_agv.id
        set_stage_paths(
            manual_task,
            [{"x": 1, "y": 3}],
            [{"x": 1, "y": 3}, {"x": 8, "y": 3}],
        )
        manual_agv.status = "running"
        manual_agv.task_id = manual_task.id
        manual_agv.clear_motion(motion_state="running")

        expect(manual_task.path_to_start is not None, "manual-finish task did not persist path_to_start before finish")
        expect(manual_task.path_to_end is not None, "manual-finish task did not persist path_to_end before finish")

        manual_finish = task_service.finish_task(manual_task_id, actor=actor)
        expect(manual_finish["task"]["path_to_start"] is None, "manual finish response retained path_to_start")
        expect(manual_finish["task"]["path_to_end"] is None, "manual finish response retained path_to_end")

        manual_task = get_task_by_id(manual_task_id)
        expect(manual_task is not None and manual_task.status == "finished", "manual-finish task did not reach finished state")
        expect(manual_task.path_to_start is None, "manual-finish task retained path_to_start after finish")
        expect(manual_task.path_to_end is None, "manual-finish task retained path_to_end after finish")
        expect(manual_task.path_length_to_start is None, "manual-finish task retained path_length_to_start after finish")
        expect(manual_task.path_length_to_end is None, "manual-finish task retained path_length_to_end after finish")

        manual_agv_runtime = next((item for item in list_agvs() if int(item.id) == int(manual_agv.id)), None)
        expect(manual_agv_runtime is not None, "manual-finish AGV missing after finish")
        expect(manual_agv_runtime.status == "idle", "manual-finish AGV did not return to idle")
        expect(manual_agv_runtime.task_id is None, "manual-finish AGV still bound to finished task")
        expect(str(getattr(manual_agv_runtime, "motion_state", "") or "") == "idle", "manual-finish AGV motion state was not cleared")


def main() -> None:
    cleanup_db_file()
    summary = initialize_runtime()
    expect(summary["database_status"] == "connected", "sqlite backend did not initialize")

    points = point_service.get_point_list()
    expect(len(points) >= 10, "default point list is unexpectedly small")

    point_service.create_or_update_point(
        PointUpsertRequest(
            id="smoke_point",
            x=9,
            y=0,
            name_key=None,
            zone_key="smoke_zone",
            custom_name="Smoke Point",
            aliases=["smoke", "9,0"],
            custom=True,
        )
    )
    scoped_point_id = build_scoped_storage_id("smoke_point")
    with get_db_session() as session:
        point_entity = session.get(PointLibraryEntity, scoped_point_id)
        expect(point_entity is not None, "saved point not found in sqlite db")
        expect(point_entity.custom is True, "saved point custom flag mismatch")

    point_service.delete_point("smoke_point")
    with get_db_session() as session:
        point_entity = session.get(PointLibraryEntity, scoped_point_id)
        expect(point_entity is None, "deleted point still exists in sqlite db")

    templates = template_service.get_template_list()
    expect(len(templates) >= 4, "default template list is unexpectedly small")

    template_service.create_or_update_template(
        TaskTemplateUpsertRequest(
            id="smoke_template",
            priority=4,
            name_key=None,
            custom_name="Smoke Template",
            custom=True,
            stages=[
                TaskTemplateStagePayload(index=0, start_x=0, start_y=0, end_x=3, end_y=2, label="pickup"),
                TaskTemplateStagePayload(index=1, start_x=3, start_y=2, end_x=6, end_y=2, label="handoff"),
            ],
        )
    )
    scoped_template_id = build_scoped_storage_id("smoke_template")
    with get_db_session() as session:
        template_entity = session.get(TaskTemplateEntity, scoped_template_id)
        expect(template_entity is not None, "saved template not found in sqlite db")
        expect(len(template_entity.stages) == 2, "saved template stage count mismatch")

    template_service.delete_template("smoke_template")
    with get_db_session() as session:
        template_entity = session.get(TaskTemplateEntity, scoped_template_id)
        expect(template_entity is None, "deleted template still exists in sqlite db")

    map_data = status_service.get_map_layout()
    expect(map_data["grid_cols"] == 10 and map_data["grid_rows"] == 8, "default grid size mismatch")

    updated_map = status_service.update_map_layout(
        [BlockedCellPayload(x=0, y=0), BlockedCellPayload(x=9, y=7)],
        None,
        10,
        8,
    )
    expect(
        blocked_cells_to_set(updated_map["blocked_cells"]) == {(0, 0), (9, 7)},
        "updated blocked cells mismatch",
    )
    with get_db_session() as session:
        layout_entity = session.get(MapLayoutEntity, 1)
        expect(layout_entity is not None, "map layout row missing in sqlite db")
        persisted_cells = {(int(cell.x), int(cell.y)) for cell in layout_entity.blocked_cells}
        expect(persisted_cells == {(0, 0), (9, 7)}, "persisted map cells mismatch")

    reset_map = status_service.reset_map_layout()
    expect(reset_map["grid_cols"] == 10 and reset_map["grid_rows"] == 8, "map reset grid size mismatch")

    assert_scope_isolation()
    assert_reserved_special_node_constraints()
    assert_ui_settings_roundtrip()
    assert_task_path_lifecycle()

    print("SQLITE_SMOKE_OK point/template/map/scope/reserved_special_node/ui_settings/task_path_lifecycle")
    cleanup_db_file()


if __name__ == "__main__":
    main()
