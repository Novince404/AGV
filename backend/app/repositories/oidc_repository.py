from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_db_session
from app.models.oidc import OIDCIdentity, OIDCLinkRequest
from app.repositories.runtime import is_sql_backend
from app.repositories.sql_models import OIDCIdentityEntity, OIDCLinkRequestEntity


_identities: list[OIDCIdentity] = []
_link_requests: dict[str, OIDCLinkRequest] = {}


def _identity_from_entity(entity: OIDCIdentityEntity) -> OIDCIdentity:
    return OIDCIdentity(
        id=entity.id,
        issuer=entity.issuer,
        subject=entity.subject,
        user_id=entity.user_id,
        email=entity.email,
        created_at=entity.created_at,
    )


def _request_from_entity(entity: OIDCLinkRequestEntity) -> OIDCLinkRequest:
    return OIDCLinkRequest.model_validate(
        {
            "id": entity.id,
            "issuer": entity.issuer,
            "subject": entity.subject,
            "email": entity.email,
            "display_name": entity.display_name,
            "status": entity.status,
            "requested_at": entity.requested_at,
            "reviewed_at": entity.reviewed_at,
            "reviewed_by": entity.reviewed_by,
            "user_id": entity.user_id,
        }
    )


def get_identity(issuer: str, subject: str) -> OIDCIdentity | None:
    if not is_sql_backend():
        return next((item for item in _identities if item.issuer == issuer and item.subject == subject), None)
    with get_db_session() as session:
        entity = session.execute(
            select(OIDCIdentityEntity).where(
                OIDCIdentityEntity.issuer == issuer,
                OIDCIdentityEntity.subject == subject,
            )
        ).scalar_one_or_none()
        return _identity_from_entity(entity) if entity else None


def upsert_identity(identity: OIDCIdentity) -> OIDCIdentity:
    if not is_sql_backend():
        existing = get_identity(identity.issuer, identity.subject)
        if existing:
            _identities[_identities.index(existing)] = identity
        else:
            identity.id = len(_identities) + 1
            _identities.append(identity)
        return identity
    with get_db_session() as session:
        entity = session.execute(
            select(OIDCIdentityEntity).where(
                OIDCIdentityEntity.issuer == identity.issuer,
                OIDCIdentityEntity.subject == identity.subject,
            )
        ).scalar_one_or_none()
        if entity is None:
            entity = OIDCIdentityEntity(issuer=identity.issuer, subject=identity.subject)
            session.add(entity)
        entity.user_id = identity.user_id
        entity.email = identity.email
        entity.created_at = identity.created_at
        session.commit()
        session.refresh(entity)
        return _identity_from_entity(entity)


def get_link_request(request_id: str) -> OIDCLinkRequest | None:
    if not is_sql_backend():
        return _link_requests.get(request_id)
    with get_db_session() as session:
        entity = session.get(OIDCLinkRequestEntity, request_id)
        return _request_from_entity(entity) if entity else None


def get_pending_request(issuer: str, subject: str) -> OIDCLinkRequest | None:
    if not is_sql_backend():
        return next(
            (item for item in _link_requests.values() if item.issuer == issuer and item.subject == subject and item.status == "pending"),
            None,
        )
    with get_db_session() as session:
        entity = session.execute(
            select(OIDCLinkRequestEntity).where(
                OIDCLinkRequestEntity.issuer == issuer,
                OIDCLinkRequestEntity.subject == subject,
                OIDCLinkRequestEntity.status == "pending",
            )
        ).scalars().first()
        return _request_from_entity(entity) if entity else None


def list_link_requests(status: str | None = "pending") -> list[OIDCLinkRequest]:
    if not is_sql_backend():
        items = list(_link_requests.values())
    else:
        with get_db_session() as session:
            query = select(OIDCLinkRequestEntity).order_by(OIDCLinkRequestEntity.requested_at.desc())
            if status:
                query = query.where(OIDCLinkRequestEntity.status == status)
            items = [_request_from_entity(entity) for entity in session.execute(query).scalars().all()]
    if status:
        items = [item for item in items if item.status == status]
    return sorted(items, key=lambda item: item.requested_at, reverse=True)


def upsert_link_request(item: OIDCLinkRequest) -> OIDCLinkRequest:
    if not is_sql_backend():
        _link_requests[item.id] = item
        return item
    with get_db_session() as session:
        entity = session.get(OIDCLinkRequestEntity, item.id) or OIDCLinkRequestEntity(id=item.id)
        entity.issuer = item.issuer
        entity.subject = item.subject
        entity.email = item.email
        entity.display_name = item.display_name
        entity.status = item.status
        entity.requested_at = item.requested_at
        entity.reviewed_at = item.reviewed_at
        entity.reviewed_by = item.reviewed_by
        entity.user_id = item.user_id
        session.add(entity)
        session.commit()
        session.refresh(entity)
        return _request_from_entity(entity)


def reset_memory_oidc() -> None:
    _identities.clear()
    _link_requests.clear()
