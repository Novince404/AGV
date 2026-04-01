from __future__ import annotations

from app.models.tracked_model import TrackedModel


class AGV(TrackedModel):
    id: int
    x: int
    y: int
    status: str
    task_id: int | None = None
    active_fault_event_id: int | None = None
    render_x: float | None = None
    render_y: float | None = None
    current_node: str | None = None
    current_edge: str | None = None
    edge_progress: float = 0.0
    motion_state: str = "idle"
    current_speed: float = 0.0
    target_speed: float = 0.0
    heading: float = 0.0
    motion_started_at: str | None = None
    motion_updated_at: str | None = None
    motion_duration_ms: int = 0
    motion_source_x: float | None = None
    motion_source_y: float | None = None
    motion_target_x: float | None = None
    motion_target_y: float | None = None

    def model_post_init(self, __context) -> None:
        if self.render_x is None:
            self.render_x = float(self.x)
        if self.render_y is None:
            self.render_y = float(self.y)
        if self.motion_source_x is None:
            self.motion_source_x = float(self.x)
        if self.motion_source_y is None:
            self.motion_source_y = float(self.y)
        if self.motion_target_x is None:
            self.motion_target_x = float(self.x)
        if self.motion_target_y is None:
            self.motion_target_y = float(self.y)

    def apply_motion_fields(self, **fields):
        self.suspend_change_notifications()
        try:
            for key, value in fields.items():
                setattr(self, key, value)
        finally:
            self.resume_change_notifications()
        self.notify_change()
        return self

    def clear_motion(self, motion_state: str = "idle"):
        return self.apply_motion_fields(
            render_x=float(self.x),
            render_y=float(self.y),
            current_node=self.current_node or f"grid:{int(self.x)}:{int(self.y)}",
            current_edge=None,
            edge_progress=0.0,
            motion_state=motion_state,
            current_speed=0.0,
            target_speed=0.0,
            heading=0.0,
            motion_started_at=None,
            motion_updated_at=None,
            motion_duration_ms=0,
            motion_source_x=float(self.x),
            motion_source_y=float(self.y),
            motion_target_x=float(self.x),
            motion_target_y=float(self.y),
        )
