from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    dispatch_origin_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_origin_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    path_to_start: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    path_to_end: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    path_length_to_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path_length_to_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dispatch_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatch_algorithm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dispatch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cell_wait_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cell_wait_retry_budget: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_stage_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_stages: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    overall_start_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_start_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_end_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_end_y: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stages: Mapped[list["TaskStageEntity"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStageEntity.stage_index",
    )


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
    path_to_start: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    path_to_end: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    path_length_to_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path_length_to_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    task: Mapped["TaskEntity"] = relationship(back_populates="stages")


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


class MapLayoutEntity(Base):
    __tablename__ = "map_layout"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_key: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    grid_cols: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_rows: Mapped[int] = mapped_column(Integer, nullable=False)

    blocked_cells: Mapped[list["MapBlockedCellEntity"]] = relationship(
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="MapBlockedCellEntity.id",
    )


class MapBlockedCellEntity(Base):
    __tablename__ = "map_blocked_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("map_layout.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    layout: Mapped["MapLayoutEntity"] = relationship(back_populates="blocked_cells")


class MapPresetEntity(Base):
    __tablename__ = "map_preset"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    custom_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom: Mapped[bool] = mapped_column(nullable=False, default=True)

    blocked_cells: Mapped[list["MapPresetCellEntity"]] = relationship(
        back_populates="preset",
        cascade="all, delete-orphan",
        order_by="MapPresetCellEntity.id",
    )


class MapPresetCellEntity(Base):
    __tablename__ = "map_preset_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[str] = mapped_column(ForeignKey("map_preset.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    preset: Mapped["MapPresetEntity"] = relationship(back_populates="blocked_cells")


class MapProfileEntity(Base):
    __tablename__ = "map_profile"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    custom_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grid_cols: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    custom: Mapped[bool] = mapped_column(nullable=False, default=True)

    blocked_cells: Mapped[list["MapProfileCellEntity"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="MapProfileCellEntity.id",
    )


class MapProfileCellEntity(Base):
    __tablename__ = "map_profile_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("map_profile.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    profile: Mapped["MapProfileEntity"] = relationship(back_populates="blocked_cells")


class UiSettingsEntity(Base):
    __tablename__ = "ui_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_minimap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_marker_icons: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_path_arrows: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_status_legend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status_legend_layout: Mapped[str] = mapped_column(String(16), nullable=False, default="horizontal")
    status_legend_opacity: Mapped[float] = mapped_column(Float, nullable=False, default=0.55)
    compare_display_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="panel")
    panel_sections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class PointLibraryEntity(Base):
    __tablename__ = "point_library"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    name_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    zone_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    custom: Mapped[bool] = mapped_column(nullable=False, default=False)


class TaskTemplateEntity(Base):
    __tablename__ = "task_template"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom: Mapped[bool] = mapped_column(nullable=False, default=False)

    stages: Mapped[list["TaskTemplateStageEntity"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TaskTemplateStageEntity.stage_index",
    )


class TaskTemplateStageEntity(Base):
    __tablename__ = "task_template_stage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("task_template.id"), nullable=False, index=True)
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_x: Mapped[int] = mapped_column(Integer, nullable=False)
    start_y: Mapped[int] = mapped_column(Integer, nullable=False)
    end_x: Mapped[int] = mapped_column(Integer, nullable=False)
    end_y: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)

    template: Mapped["TaskTemplateEntity"] = relationship(back_populates="stages")
