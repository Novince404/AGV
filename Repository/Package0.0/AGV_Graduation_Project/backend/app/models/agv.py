from __future__ import annotations

from datetime import datetime

from app.models.tracked_model import TrackedModel


class AGV(TrackedModel):
    id: int
    scope_key: str | None = None
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
    segment_mode: str = "grid"
    current_lane_type: str | None = None
    current_speed_multiplier: float = 1.0
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
    battery_level: float = 100.0
    energy_updated_at: str | None = None
    idle_since_at: str | None = None
    charge_started_at: str | None = None
    auto_target_node: str | None = None
    auto_target_type: str | None = None

    def model_post_init(self, __context) -> None:
        now_iso = datetime.now().isoformat(timespec="seconds")
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
        if self.energy_updated_at is None:
            self.energy_updated_at = now_iso
        if self.status == "idle" and self.idle_since_at is None and self.task_id is None:
            self.idle_since_at = now_iso

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
            segment_mode="grid",
            current_lane_type=None,
            current_speed_multiplier=1.0,
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
