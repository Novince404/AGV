from __future__ import annotations

from app.models.tracked_model import TrackedModel


class MapPresetCell(TrackedModel):
    x: int
    y: int


class MapPreset(TrackedModel):
    key: str
    custom_name: str
    description: str | None = None
    valid_cells: list[MapPresetCell] = []
    blocked_cells: list[MapPresetCell] = []
    custom: bool = True

    def bind_on_change(self, callback):
        super().bind_on_change(callback)
        for cell in self.valid_cells:
            if hasattr(cell, "bind_on_change"):
                cell.bind_on_change(self._notify_change)
        for cell in self.blocked_cells:
            if hasattr(cell, "bind_on_change"):
                cell.bind_on_change(self._notify_change)
        return self
