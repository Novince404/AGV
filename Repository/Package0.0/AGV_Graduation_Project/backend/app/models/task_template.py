from __future__ import annotations

from app.models.tracked_model import TrackedModel


class TaskTemplateStage(TrackedModel):
    index: int
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    label: str | None = None


class TaskTemplate(TrackedModel):
    id: str
    priority: int = 1
    name_key: str | None = None
    custom_name: str | None = None
    custom: bool = False
    stages: list[TaskTemplateStage] = []

    def bind_on_change(self, callback):
        super().bind_on_change(callback)
        for stage in self.stages:
            if hasattr(stage, "bind_on_change"):
                stage.bind_on_change(self._notify_change)
        return self
