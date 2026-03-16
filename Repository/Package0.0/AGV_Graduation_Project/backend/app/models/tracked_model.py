from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, PrivateAttr


class TrackedModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _on_change: Callable[[], None] | None = PrivateAttr(default=None)
    _change_notifications_enabled: bool = PrivateAttr(default=True)

    def bind_on_change(self, callback: Callable[[], None] | None):
        self._on_change = callback
        return self

    def suspend_change_notifications(self):
        self._change_notifications_enabled = False
        return self

    def resume_change_notifications(self):
        self._change_notifications_enabled = True
        return self

    def _notify_change(self):
        if self._change_notifications_enabled and self._on_change:
            self._on_change()

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        previous = getattr(self, name, object())
        super().__setattr__(name, value)
        if previous != value:
            self._notify_change()
