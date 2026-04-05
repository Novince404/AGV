from app.models.agv import AGV


agv_list = [
    AGV(id=1, x=2, y=3, status="idle"),
    AGV(id=2, x=5, y=7, status="idle"),
    AGV(id=3, x=1, y=4, status="idle"),
]


def list_agvs() -> list[AGV]:
    return agv_list


def get_agv_by_id(agv_id: int) -> AGV | None:
    return next((agv for agv in agv_list if agv.id == agv_id), None)


def list_idle_agvs() -> list[AGV]:
    return [agv for agv in agv_list if agv.status in {"idle", "idle_returning"}]


def get_first_idle_agv() -> AGV | None:
    return next((agv for agv in agv_list if agv.status in {"idle", "idle_returning"}), None)


def create_agv(agv: AGV) -> AGV:
    next_id = max((item.id for item in agv_list), default=0) + 1
    created = AGV(**{**agv.model_dump(), "id": next_id})
    agv_list.append(created)
    return created
