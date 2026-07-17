from __future__ import annotations

import asyncio
import os
import socket
from contextlib import suppress
from uuid import uuid4

from app.core.events import event_broker
from app.core.settings import get_settings
from app.devices.simulation import SimulationDeviceAdapter
from app.devices.types import DeviceCommand, TelemetrySnapshot
from app.repositories import runtime_repository


class DeterministicCoordinator:
    """Runs every simulated vehicle in one ordered, fixed-duration time step."""

    lease_key = "primary-dispatch-coordinator"

    def __init__(self, adapter: SimulationDeviceAdapter | None = None) -> None:
        settings = get_settings()
        self.tick_seconds = settings.scheduler_tick_ms / 1000
        self.lease_ttl_sec = settings.scheduler_lease_ttl_sec
        self.owner_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        self.adapter = adapter or SimulationDeviceAdapter()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._last_snapshots: dict[str, tuple] = {}
        self._agv_scopes: dict[str, str] = {}
        self.is_leader = False
        self.tick_count = 0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        await self.adapter.start(self._handle_telemetry)
        self._task = asyncio.create_task(self.run(), name="agv-deterministic-coordinator")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        await self.adapter.stop()
        self.is_leader = False

    async def run(self) -> None:
        while not self._stop.is_set():
            await self.tick()
            await asyncio.sleep(self.tick_seconds)

    async def tick(self) -> None:
        self.is_leader = runtime_repository.acquire_or_renew_lease(
            self.lease_key,
            self.owner_id,
            self.lease_ttl_sec,
        )
        if not self.is_leader:
            return
        for queued in runtime_repository.claim_pending_commands():
            try:
                payload = dict(queued.payload)
                command = DeviceCommand(
                    id=queued.id,
                    agv_id=str(queued.entity_id or payload.get("agv_id", "")),
                    command_type=queued.command_type,
                    parameters=dict(payload.get("parameters") or {}),
                    requested_at=payload.get("requested_at") or queued.created_at,
                    idempotency_key=queued.idempotency_key,
                )
                self._agv_scopes[command.agv_id] = queued.scope_key
                receipt = await self.adapter.send(command)
                runtime_repository.complete_command(
                    queued.id,
                    status="completed" if receipt.accepted else "rejected",
                    result=receipt.model_dump(),
                )
                self._publish(
                    "device.command.completed",
                    scope_key=queued.scope_key,
                    entity_type="agv",
                    entity_id=queued.entity_id,
                    correlation_id=queued.id,
                    data=receipt.model_dump(),
                )
            except Exception as exc:
                runtime_repository.complete_command(
                    queued.id,
                    status="failed",
                    result={"error": type(exc).__name__, "message": str(exc)},
                )
        await self.adapter.advance(self.tick_seconds)
        self.tick_count += 1

    async def _handle_telemetry(self, snapshot: TelemetrySnapshot) -> None:
        state_key = (
            round(snapshot.x, 6),
            round(snapshot.y, 6),
            round(snapshot.speed, 6),
            round(snapshot.battery, 6),
            snapshot.status,
        )
        if self._last_snapshots.get(snapshot.agv_id) == state_key:
            return
        self._last_snapshots[snapshot.agv_id] = state_key
        self._publish(
            "agv.state.changed",
            scope_key=self._agv_scopes.get(snapshot.agv_id, "system"),
            entity_type="agv",
            entity_id=snapshot.agv_id,
            data=snapshot.model_dump(),
        )

    @staticmethod
    def _publish(
        event_type: str,
        *,
        scope_key: str,
        entity_type: str,
        entity_id: str | None,
        correlation_id: str | None = None,
        data: dict | None = None,
    ) -> None:
        event = runtime_repository.append_event(
            event_type,
            scope_key=scope_key,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            data=data,
        )
        event_broker.publish_event(event)


coordinator = DeterministicCoordinator()
