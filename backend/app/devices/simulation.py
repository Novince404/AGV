from __future__ import annotations

import asyncio
import math

from app.devices.base import TelemetryHandler
from app.devices.types import CommandReceipt, DeviceCommand, DeviceHealth, TelemetrySnapshot, utc_now_iso


class SimulationDeviceAdapter:
    """Deterministic software-only adapter; no real device I/O is performed."""

    def __init__(self) -> None:
        self._handler: TelemetryHandler | None = None
        self._states: dict[str, TelemetrySnapshot] = {}
        self._targets: dict[str, tuple[float, float, float]] = {}
        self._receipts: dict[str, CommandReceipt] = {}
        self._running = False
        self._last_heartbeat: str | None = None
        self._lock = asyncio.Lock()

    async def start(self, event_handler: TelemetryHandler) -> None:
        self._handler = event_handler
        self._running = True
        self._last_heartbeat = utc_now_iso()

    async def stop(self) -> None:
        self._running = False
        self._handler = None

    async def send(self, command: DeviceCommand) -> CommandReceipt:
        if command.idempotency_key and command.idempotency_key in self._receipts:
            return self._receipts[command.idempotency_key]
        async with self._lock:
            state = self._states.setdefault(command.agv_id, TelemetrySnapshot(agv_id=command.agv_id, x=0, y=0))
            accepted = True
            reason = None
            if command.command_type == "move_to":
                try:
                    target_x = float(command.parameters["x"])
                    target_y = float(command.parameters["y"])
                    speed = max(float(command.parameters.get("speed", 1.0)), 0.01)
                    self._targets[command.agv_id] = (target_x, target_y, speed)
                    state.status = "moving"
                except (KeyError, TypeError, ValueError):
                    accepted = False
                    reason = "invalid_move_target"
            elif command.command_type == "stop":
                self._targets.pop(command.agv_id, None)
                state.speed = 0.0
                state.status = "stopped"
            elif command.command_type == "resume":
                state.status = "idle" if command.agv_id not in self._targets else "moving"
            elif command.command_type == "set_battery":
                try:
                    state.battery = min(max(float(command.parameters["battery"]), 0.0), 100.0)
                except (KeyError, TypeError, ValueError):
                    accepted = False
                    reason = "invalid_battery_value"
            receipt = CommandReceipt(
                command_id=command.id,
                accepted=accepted,
                status="accepted" if accepted else "rejected",
                reason=reason,
            )
            if command.idempotency_key:
                self._receipts[command.idempotency_key] = receipt
            return receipt

    async def advance(self, delta_sec: float) -> list[TelemetrySnapshot]:
        emitted: list[TelemetrySnapshot] = []
        if not self._running:
            return emitted
        async with self._lock:
            for agv_id in sorted(self._states):
                state = self._states[agv_id]
                target = self._targets.get(agv_id)
                if target and state.status != "stopped":
                    target_x, target_y, speed = target
                    dx, dy = target_x - state.x, target_y - state.y
                    distance = math.hypot(dx, dy)
                    step = speed * max(delta_sec, 0.0)
                    if distance <= step or distance == 0:
                        state.x, state.y = target_x, target_y
                        state.speed = 0.0
                        state.status = "idle"
                        self._targets.pop(agv_id, None)
                    else:
                        state.x += dx / distance * step
                        state.y += dy / distance * step
                        state.speed = speed
                        state.status = "moving"
                        state.battery = max(state.battery - delta_sec * 0.01, 0.0)
                state.device_time = utc_now_iso()
                emitted.append(state.model_copy(deep=True))
            self._last_heartbeat = utc_now_iso()
        if self._handler:
            for snapshot in emitted:
                await self._handler(snapshot)
        return emitted

    async def health(self) -> DeviceHealth:
        return DeviceHealth(
            adapter="simulation",
            connected=self._running,
            last_heartbeat=self._last_heartbeat,
            details={"agv_count": len(self._states), "target_count": len(self._targets)},
        )
