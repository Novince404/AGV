from __future__ import annotations

from sqlalchemy import delete, inspect, select, text

from app.core.auth_capabilities import normalize_role
from app.core.auth_defaults import build_default_auth_users
from app.core.database import get_engine
from app.core.database import get_db_session
from app.models.auth import AuthSession, AuthUser
from app.repositories.db_init import create_all_tables
from app.repositories.sql_models import AuthSessionEntity, AuthUserEntity


def _entity_to_user(entity: AuthUserEntity) -> AuthUser:
    return AuthUser(
        id=entity.id,
        username=entity.username,
        display_name=entity.display_name,
        role=normalize_role(entity.role),
        password_hash=entity.password_hash,
        active=bool(entity.active),
        builtin=bool(entity.builtin),
        account_status=str(getattr(entity, "account_status", "approved") or "approved"),
        organization_id=getattr(entity, "organization_id", None),
        organization_name=getattr(entity, "organization_name", None),
    )


def _user_to_entity(user: AuthUser, entity: AuthUserEntity | None = None) -> AuthUserEntity:
    entity = entity or AuthUserEntity(id=user.id)
    entity.username = user.username
    entity.display_name = user.display_name
    entity.role = normalize_role(user.role)
    entity.password_hash = user.password_hash
    entity.active = bool(user.active)
    entity.builtin = bool(user.builtin)
    entity.account_status = str(user.account_status or "approved")
    entity.organization_id = user.organization_id
    entity.organization_name = user.organization_name
    return entity


def _entity_to_session(entity: AuthSessionEntity) -> AuthSession:
    return AuthSession(
        token=entity.token,
        user_id=entity.user_id,
        created_at=int(entity.created_at),
        expires_at=int(entity.expires_at),
        last_seen_at=int(entity.last_seen_at),
    )


def _session_to_entity(session_model: AuthSession, entity: AuthSessionEntity | None = None) -> AuthSessionEntity:
    entity = entity or AuthSessionEntity(token=session_model.token)
    entity.user_id = session_model.user_id
    entity.created_at = int(session_model.created_at)
    entity.expires_at = int(session_model.expires_at)
    entity.last_seen_at = int(session_model.last_seen_at)
    return entity


def _ensure_schema() -> None:
    create_all_tables()
    engine = get_engine()
    inspector = inspect(engine)
    if "auth_user" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("auth_user")}
    ddl_statements: list[str] = []
    if "account_status" not in columns:
        ddl_statements.append("ALTER TABLE auth_user ADD COLUMN account_status VARCHAR(32) NOT NULL DEFAULT 'approved'")
    if "organization_id" not in columns:
        ddl_statements.append("ALTER TABLE auth_user ADD COLUMN organization_id VARCHAR(64)")
    if "organization_name" not in columns:
        ddl_statements.append("ALTER TABLE auth_user ADD COLUMN organization_name VARCHAR(128)")

    if ddl_statements:
        with engine.begin() as connection:
            for statement in ddl_statements:
                connection.execute(text(statement))


def _sync_default_users() -> None:
    with get_db_session() as session:
        for default_user in build_default_auth_users():
            entity = session.get(AuthUserEntity, default_user.id)
            if entity is None:
                session.add(_user_to_entity(default_user))
                continue

            entity.role = normalize_role(entity.role)
            if bool(entity.builtin):
                entity.display_name = default_user.display_name
                entity.active = bool(default_user.active)
                entity.builtin = bool(default_user.builtin)
                entity.account_status = str(default_user.account_status or "approved")
                entity.organization_id = default_user.organization_id
                entity.organization_name = default_user.organization_name
        session.commit()


def _ensure_ready() -> None:
    _ensure_schema()
    _sync_default_users()


def list_users() -> list[AuthUser]:
    _ensure_ready()
    with get_db_session() as session:
        entities = session.execute(select(AuthUserEntity).order_by(AuthUserEntity.username)).scalars().all()
    return [_entity_to_user(entity) for entity in entities]


def get_user_by_id(user_id: str) -> AuthUser | None:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(AuthUserEntity, str(user_id or ""))
    return _entity_to_user(entity) if entity is not None else None


def get_user_by_username(username: str) -> AuthUser | None:
    _ensure_ready()
    normalized = str(username or "").strip()
    if not normalized:
        return None
    with get_db_session() as session:
        entity = session.execute(select(AuthUserEntity).where(AuthUserEntity.username == normalized)).scalar_one_or_none()
    return _entity_to_user(entity) if entity is not None else None


def upsert_user(user: AuthUser) -> AuthUser:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(AuthUserEntity, user.id)
        entity = _user_to_entity(user, entity)
        session.add(entity)
        session.commit()
        session.refresh(entity)
    return _entity_to_user(entity)


def get_session_by_token(token: str) -> AuthSession | None:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(AuthSessionEntity, str(token or ""))
    return _entity_to_session(entity) if entity is not None else None


def upsert_session(session_model: AuthSession) -> AuthSession:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(AuthSessionEntity, session_model.token)
        entity = _session_to_entity(session_model, entity)
        session.add(entity)
        session.commit()
        session.refresh(entity)
    return _entity_to_session(entity)


def remove_session(token: str) -> None:
    _ensure_ready()
    with get_db_session() as session:
        entity = session.get(AuthSessionEntity, str(token or ""))
        if entity is not None:
            session.delete(entity)
            session.commit()


def remove_sessions_for_user(user_id: str) -> None:
    _ensure_ready()
    with get_db_session() as session:
        session.execute(delete(AuthSessionEntity).where(AuthSessionEntity.user_id == str(user_id or "")))
        session.commit()
