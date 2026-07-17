from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeviceCommandRequest(BaseModel):
    command_type: Literal["move_to", "stop", "resume", "set_battery"]
    parameters: dict[str, Any] = Field(default_factory=dict)
