from __future__ import annotations

from app.core.database import get_engine
from app.repositories.sql_models import Base


def create_all_tables() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

