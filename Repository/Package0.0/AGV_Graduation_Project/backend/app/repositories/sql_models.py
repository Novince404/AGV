from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AgvEntity(Base):
    __tablename__ = "agv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_fault_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TaskEntity(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_x: Mapped[int] = mapped_column(Integer, nullable=False)
    start_y: Mapped[int] = mapped_column(Integer, nullable=False)
    end_x: Mapped[int] = mapped_column(Integer, nullable=False)
    end_y: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    agv_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_agv_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dispatch_algorithm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dispatch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class TaskStageEntity(Base):
    __tablename__ = "task_stage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task.id"), nullable=False, index=True)
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_x: Mapped[int] = mapped_column(Integer, nullable=False)
    start_y: Mapped[int] = mapped_column(Integer, nullable=False)
    end_x: Mapped[int] = mapped_column(Integer, nullable=False)
    end_y: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class FaultEventEntity(Base):
    __tablename__ = "fault_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agv_id: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fault_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fault")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    reported_at: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reported_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
