from __future__ import annotations

from app.models.tracked_model import TrackedModel


class OperationAudit(TrackedModel):
    id: int
    resource_type: str
    resource_id: str
    action: str
    operator_id: str | None = None
    operator_username: str = "guest"
    operator_display_name: str = "Guest"
    operator_role: str = "guest"
    performed_at: str
    metadata: dict | None = None
