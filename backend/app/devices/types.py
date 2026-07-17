from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class DeviceCommand(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    agv_id: str
    command_type: Literal["move_to", "stop", "resume", "set_battery"]
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_at: str = Field(default_factory=utc_now_iso)
    idempotency_key: str | None = None


class TelemetrySnapshot(BaseModel):
    agv_id: str
    x: float
    y: float
    speed: float = 0.0
    battery: float = 100.0
    status: str = "idle"
    device_time: str = Field(default_factory=utc_now_iso)


class CommandReceipt(BaseModel):
    command_id: str
    accepted: bool
    status: str
    reason: str | None = None
    received_at: str = Field(default_factory=utc_now_iso)


class DeviceHealth(BaseModel):
    adapter: str
    connected: bool
    last_heartbeat: str | None = None
    latency_ms: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
