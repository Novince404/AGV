from __future__ import annotations

import asyncio

from app.devices.simulation import SimulationDeviceAdapter
from app.repositories import runtime_repository
from app.scheduler.coordinator import DeterministicCoordinator


def test_deterministic_coordinator_processes_commands_and_persists_events():
    async def scenario():
        adapter = SimulationDeviceAdapter()
        coordinator = DeterministicCoordinator(adapter)
        await adapter.start(coordinator._handle_telemetry)
        _command, created = runtime_repository.enqueue_command(
            command_type="move_to",
            scope_key="organization:test",
            entity_id="AGV-7",
            payload={"agv_id": "AGV-7", "parameters": {"x": 1, "y": 0, "speed": 10}},
            idempotency_key="runtime-command-0001",
        )
        assert created
        await coordinator.tick()
        assert coordinator.is_leader
        events = runtime_repository.list_events_after(None, scope_key="organization:test")
        assert [event.type for event in events] == [
            "device.command.queued",
            "device.command.completed",
            "agv.state.changed",
        ]
        assert events[-1].data["x"] == 1
        assert runtime_repository.get_lease(coordinator.lease_key)["owner_id"] == coordinator.owner_id
        await adapter.stop()

    asyncio.run(scenario())


def test_simulation_replay_is_deterministic():
    async def replay():
        states = []

        async def collect(snapshot):
            states.append((snapshot.agv_id, round(snapshot.x, 4), round(snapshot.y, 4), snapshot.status))

        adapter = SimulationDeviceAdapter()
        await adapter.start(collect)
        from app.devices.types import DeviceCommand

        await adapter.send(
            DeviceCommand(agv_id="A", command_type="move_to", parameters={"x": 1, "y": 1, "speed": 1})
        )
        for _ in range(4):
            await adapter.advance(0.25)
        await adapter.stop()
        return states

    assert asyncio.run(replay()) == asyncio.run(replay())
