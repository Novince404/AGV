from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE_DB_PATH = BACKEND_DIR / "agv_dispatch_smoke.db"
SMOKE_DB_URL = f"sqlite:///{SMOKE_DB_PATH.as_posix()}"

os.environ["AGV_DATA_BACKEND"] = "sqlite"
os.environ["AGV_DATABASE_URL"] = SMOKE_DB_URL
os.environ["AGV_DATABASE_AUTO_CREATE"] = "true"

sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import dispose_engine, get_db_session  # noqa: E402
from app.core.data_scope import build_scoped_storage_id  # noqa: E402
from app.core.lifecycle import initialize_runtime  # noqa: E402
from app.repositories.sql_models import MapLayoutEntity, PointLibraryEntity, TaskTemplateEntity  # noqa: E402
from app.schemas.point import PointUpsertRequest  # noqa: E402
from app.schemas.status import BlockedCellPayload  # noqa: E402
from app.schemas.template import TaskTemplateStagePayload, TaskTemplateUpsertRequest  # noqa: E402
from app.services import point_service, status_service, template_service  # noqa: E402


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

    print("SQLITE_SMOKE_OK point/template/map")
    cleanup_db_file()


if __name__ == "__main__":
    main()
