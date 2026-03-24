from __future__ import annotations

from app.models.tracked_model import TrackedModel


class EnterpriseApplication(TrackedModel):
    id: int
    company_name: str
    contact_name: str
    contact_email: str
    username: str
    user_id: str
    status: str = "pending"
    submitted_at: str
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    review_note: str | None = None
    organization_id: str | None = None
