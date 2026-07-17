from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db_session
from app.core.events import RuntimeEvent
from app.repositories.runtime import is_memory_backend
from app.repositories.sql_models import IdempotencyRecordEntity, RuntimeCommandEntity, RuntimeEventEntity, SchedulerLeaseEntity


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="milliseconds")


def _request_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stored_idempotency_key(scope_key: str, key: str | None) -> str | None:
    if not key:
        return None
    return hashlib.sha256(f"{scope_key}\0{key}".encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class QueuedCommand:
    id: str
    command_type: str
    scope_key: str
    entity_id: str | None
    status: str
    idempotency_key: str | None
    created_at: str
    payload: dict
    result: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "command_type": self.command_type,
            "scope_key": self.scope_key,
            "entity_id": self.entity_id,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at,
            "payload": self.payload,
            "result": self.result,
        }


_memory_lock = threading.RLock()
_memory_commands: dict[str, QueuedCommand] = {}
_memory_idempotency: dict[str, str] = {}
_memory_events: list[RuntimeEvent] = []
_memory_leases: dict[str, tuple[str, datetime]] = {}
_memory_responses: dict[tuple[str, str], tuple[str, int, dict]] = {}


def _command_from_entity(entity: RuntimeCommandEntity) -> QueuedCommand:
    payload = dict(entity.payload or {})
    return QueuedCommand(
        id=entity.id,
        command_type=entity.command_type,
        scope_key=entity.scope_key,
        entity_id=entity.entity_id,
        status=entity.status,
        idempotency_key=payload.get("idempotency_key"),
        created_at=entity.created_at,
        payload=payload,
        result=dict(entity.result) if entity.result else None,
    )


def enqueue_command(
    *,
    command_type: str,
    scope_key: str,
    entity_id: str | None,
    payload: dict,
    idempotency_key: str | None = None,
) -> tuple[QueuedCommand, bool]:
    command_id = uuid4().hex
    created_at = _iso()
    normalized_payload = dict(payload)
    normalized_payload["request_hash"] = _request_hash(payload)
    if idempotency_key:
        normalized_payload["idempotency_key"] = idempotency_key
    storage_key = _stored_idempotency_key(scope_key, idempotency_key)

    if is_memory_backend():
        with _memory_lock:
            if storage_key and storage_key in _memory_idempotency:
                existing = _memory_commands[_memory_idempotency[storage_key]]
                if existing.payload.get("request_hash") != normalized_payload["request_hash"]:
                    raise ValueError("idempotency_key_payload_mismatch")
                return existing, False
            command = QueuedCommand(
                id=command_id,
                command_type=command_type,
                scope_key=scope_key,
                entity_id=entity_id,
                status="pending",
                idempotency_key=idempotency_key,
                created_at=created_at,
                payload=normalized_payload,
            )
            _memory_commands[command.id] = command
            if storage_key:
                _memory_idempotency[storage_key] = command.id
            _memory_events.append(
                RuntimeEvent(
                    id=str(len(_memory_events) + 1),
                    type="device.command.queued",
                    occurred_at=created_at,
                    scope_key=scope_key,
                    entity_type="agv",
                    entity_id=entity_id,
                    correlation_id=command.id,
                    data={"command_type": command_type, "parameters": dict(payload.get("parameters") or {})},
                )
            )
            return command, True

    entity = RuntimeCommandEntity(
        id=command_id,
        command_type=command_type,
        scope_key=scope_key,
        entity_id=entity_id,
        status="pending",
        idempotency_key=storage_key,
        created_at=created_at,
        payload=normalized_payload,
    )
    with get_db_session() as session:
        session.add(entity)
        session.add(
            RuntimeEventEntity(
                event_type="device.command.queued",
                occurred_at=created_at,
                scope_key=scope_key,
                entity_type="agv",
                entity_id=entity_id,
                correlation_id=command_id,
                payload={"command_type": command_type, "parameters": dict(payload.get("parameters") or {})},
            )
        )
        try:
            session.commit()
            session.refresh(entity)
            return _command_from_entity(entity), True
        except IntegrityError:
            session.rollback()
            if not storage_key:
                raise
            existing = session.scalar(
                select(RuntimeCommandEntity).where(RuntimeCommandEntity.idempotency_key == storage_key)
            )
            if existing is None:
                raise
            command = _command_from_entity(existing)
            if command.payload.get("request_hash") != normalized_payload["request_hash"]:
                raise ValueError("idempotency_key_payload_mismatch")
            return command, False


def get_idempotent_response(
    *,
    scope_key: str,
    idempotency_key: str,
    request_payload: dict,
) -> tuple[int, dict] | None:
    """Return a prior response for the same scoped request, or reserve nothing.

    Callers must save the response after completing their domain transaction. A
    mismatched body with the same key is always rejected instead of replayed.
    """
    request_hash = _request_hash(request_payload)
    if is_memory_backend():
        with _memory_lock:
            record = _memory_responses.get((scope_key, idempotency_key))
        if record is None:
            return None
        stored_hash, status, body = record
        if stored_hash != request_hash:
            raise ValueError("idempotency_key_payload_mismatch")
        return status, dict(body)
    with get_db_session() as session:
        entity = session.scalar(
            select(IdempotencyRecordEntity).where(
                IdempotencyRecordEntity.scope_key == scope_key,
                IdempotencyRecordEntity.idempotency_key == idempotency_key,
            )
        )
        if entity is None:
            return None
        if entity.request_hash != request_hash:
            raise ValueError("idempotency_key_payload_mismatch")
        return entity.response_status, dict(entity.response_body or {})


def save_idempotent_response(
    *,
    scope_key: str,
    idempotency_key: str,
    request_payload: dict,
    response_status: int,
    response_body: dict,
) -> tuple[int, dict]:
    request_hash = _request_hash(request_payload)
    if is_memory_backend():
        with _memory_lock:
            existing = _memory_responses.get((scope_key, idempotency_key))
            if existing:
                if existing[0] != request_hash:
                    raise ValueError("idempotency_key_payload_mismatch")
                return existing[1], dict(existing[2])
            _memory_responses[(scope_key, idempotency_key)] = (
                request_hash,
                int(response_status),
                dict(response_body),
            )
        return int(response_status), dict(response_body)
    with get_db_session() as session:
        entity = IdempotencyRecordEntity(
            scope_key=scope_key,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            response_status=int(response_status),
            response_body=dict(response_body),
            created_at=_iso(),
        )
        session.add(entity)
        try:
            session.commit()
            return entity.response_status, dict(entity.response_body)
        except IntegrityError:
            session.rollback()
            existing = session.scalar(
                select(IdempotencyRecordEntity).where(
                    IdempotencyRecordEntity.scope_key == scope_key,
                    IdempotencyRecordEntity.idempotency_key == idempotency_key,
                )
            )
            if existing is None:
                raise
            if existing.request_hash != request_hash:
                raise ValueError("idempotency_key_payload_mismatch")
            return existing.response_status, dict(existing.response_body or {})


def claim_pending_commands(limit: int = 100) -> list[QueuedCommand]:
    claimed_at = _iso()
    if is_memory_backend():
        claimed: list[QueuedCommand] = []
        with _memory_lock:
            for command in sorted(_memory_commands.values(), key=lambda item: (item.created_at, item.id)):
                if command.status != "pending" or len(claimed) >= limit:
                    continue
                processing = QueuedCommand(**{**command.to_dict(), "status": "processing"})
                _memory_commands[command.id] = processing
                claimed.append(processing)
        return claimed

    with get_db_session() as session:
        statement = (
            select(RuntimeCommandEntity)
            .where(RuntimeCommandEntity.status == "pending")
            .order_by(RuntimeCommandEntity.created_at, RuntimeCommandEntity.id)
            .limit(max(1, limit))
            .with_for_update(skip_locked=True)
        )
        entities = list(session.scalars(statement).all())
        for entity in entities:
            entity.status = "processing"
            entity.claimed_at = claimed_at
        session.commit()
        return [_command_from_entity(entity) for entity in entities]


def complete_command(command_id: str, *, status: str, result: dict) -> QueuedCommand | None:
    if is_memory_backend():
        with _memory_lock:
            command = _memory_commands.get(command_id)
            if command is None:
                return None
            updated = QueuedCommand(**{**command.to_dict(), "status": status, "result": dict(result)})
            _memory_commands[command_id] = updated
            return updated

    with get_db_session() as session:
        entity = session.get(RuntimeCommandEntity, command_id)
        if entity is None:
            return None
        entity.status = status
        entity.result = dict(result)
        entity.completed_at = _iso()
        session.commit()
        session.refresh(entity)
        return _command_from_entity(entity)


def acquire_or_renew_lease(lease_key: str, owner_id: str, ttl_sec: int) -> bool:
    now = _now()
    expires = now + timedelta(seconds=max(ttl_sec, 1))
    if is_memory_backend():
        with _memory_lock:
            current = _memory_leases.get(lease_key)
            if current and current[0] != owner_id and current[1] > now:
                return False
            _memory_leases[lease_key] = (owner_id, expires)
            return True

    with get_db_session() as session:
        entity = session.get(SchedulerLeaseEntity, lease_key, with_for_update=True)
        if entity is None:
            entity = SchedulerLeaseEntity(
                lease_key=lease_key,
                owner_id=owner_id,
                acquired_at=_iso(now),
                heartbeat_at=_iso(now),
                expires_at=_iso(expires),
            )
            session.add(entity)
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
        current_expiry = datetime.fromisoformat(entity.expires_at)
        if entity.owner_id != owner_id and current_expiry > now:
            return False
        if entity.owner_id != owner_id:
            entity.owner_id = owner_id
            entity.acquired_at = _iso(now)
        entity.heartbeat_at = _iso(now)
        entity.expires_at = _iso(expires)
        session.commit()
        return True


def get_lease(lease_key: str) -> dict | None:
    if is_memory_backend():
        with _memory_lock:
            value = _memory_leases.get(lease_key)
        if not value:
            return None
        return {"lease_key": lease_key, "owner_id": value[0], "expires_at": _iso(value[1])}
    with get_db_session() as session:
        entity = session.get(SchedulerLeaseEntity, lease_key)
        if entity is None:
            return None
        return {
            "lease_key": entity.lease_key,
            "owner_id": entity.owner_id,
            "acquired_at": entity.acquired_at,
            "heartbeat_at": entity.heartbeat_at,
            "expires_at": entity.expires_at,
        }


def append_event(
    event_type: str,
    *,
    scope_key: str,
    entity_type: str,
    entity_id: str | None,
    correlation_id: str | None = None,
    data: dict | None = None,
) -> RuntimeEvent:
    occurred_at = _iso()
    if is_memory_backend():
        with _memory_lock:
            event = RuntimeEvent(
                id=str(len(_memory_events) + 1),
                type=event_type,
                occurred_at=occurred_at,
                scope_key=scope_key,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                data=dict(data or {}),
            )
            _memory_events.append(event)
            return event

    with get_db_session() as session:
        entity = RuntimeEventEntity(
            event_type=event_type,
            occurred_at=occurred_at,
            scope_key=scope_key,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            payload=dict(data or {}),
        )
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return RuntimeEvent(
            id=str(entity.id),
            type=entity.event_type,
            occurred_at=entity.occurred_at,
            scope_key=entity.scope_key,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            correlation_id=entity.correlation_id,
            data=dict(entity.payload or {}),
        )


def list_events_after(event_id: str | None, *, scope_key: str | None = None, limit: int = 200) -> list[RuntimeEvent]:
    try:
        marker = max(int(event_id or 0), 0)
    except (TypeError, ValueError):
        marker = 0
    if is_memory_backend():
        with _memory_lock:
            events = list(_memory_events)
        return [event for event in events if int(event.id) > marker and (not scope_key or event.scope_key == scope_key)][:limit]
    with get_db_session() as session:
        statement = select(RuntimeEventEntity).where(RuntimeEventEntity.id > marker)
        if scope_key:
            statement = statement.where(RuntimeEventEntity.scope_key == scope_key)
        entities = list(session.scalars(statement.order_by(RuntimeEventEntity.id).limit(max(1, limit))).all())
        return [
            RuntimeEvent(
                id=str(entity.id),
                type=entity.event_type,
                occurred_at=entity.occurred_at,
                scope_key=entity.scope_key,
                entity_type=entity.entity_type,
                entity_id=entity.entity_id,
                correlation_id=entity.correlation_id,
                data=dict(entity.payload or {}),
            )
            for entity in entities
        ]


def reset_memory_runtime() -> None:
    with _memory_lock:
        _memory_commands.clear()
        _memory_idempotency.clear()
        _memory_events.clear()
        _memory_leases.clear()
        _memory_responses.clear()
