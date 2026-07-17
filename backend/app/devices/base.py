from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from app.devices.types import CommandReceipt, DeviceCommand, DeviceHealth, TelemetrySnapshot


TelemetryHandler = Callable[[TelemetrySnapshot], Awaitable[None]]


class DeviceAdapter(Protocol):
    async def start(self, event_handler: TelemetryHandler) -> None: ...

    async def stop(self) -> None: ...

    async def send(self, command: DeviceCommand) -> CommandReceipt: ...

    async def health(self) -> DeviceHealth: ...
