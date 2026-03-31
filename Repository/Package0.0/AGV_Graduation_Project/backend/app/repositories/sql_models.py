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
    valid_cells: Mapped[list["MapValidCellEntity"]] = relationship(
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="MapValidCellEntity.id",
    )
    topology_nodes: Mapped[list["MapLayoutTopologyNodeEntity"]] = relationship(
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="MapLayoutTopologyNodeEntity.id",
    )
    topology_edges: Mapped[list["MapLayoutTopologyEdgeEntity"]] = relationship(
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="MapLayoutTopologyEdgeEntity.id",
    )


class MapBlockedCellEntity(Base):
    __tablename__ = "map_blocked_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("map_layout.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    layout: Mapped["MapLayoutEntity"] = relationship(back_populates="blocked_cells")


class MapValidCellEntity(Base):
    __tablename__ = "map_valid_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("map_layout.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    layout: Mapped["MapLayoutEntity"] = relationship(back_populates="valid_cells")


class MapLayoutTopologyNodeEntity(Base):
    __tablename__ = "map_layout_topology_node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("map_layout.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(64), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default="waypoint")

    layout: Mapped["MapLayoutEntity"] = relationship(back_populates="topology_nodes")


class MapLayoutTopologyEdgeEntity(Base):
    __tablename__ = "map_layout_topology_edge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layout_id: Mapped[int] = mapped_column(ForeignKey("map_layout.id"), nullable=False, index=True)
    edge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="bidirectional")
    lane_type: Mapped[str] = mapped_column(String(32), nullable=False, default="main")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    speed_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    layout: Mapped["MapLayoutEntity"] = relationship(back_populates="topology_edges")


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
    valid_cells: Mapped[list["MapPresetValidCellEntity"]] = relationship(
        back_populates="preset",
        cascade="all, delete-orphan",
        order_by="MapPresetValidCellEntity.id",
    )


class MapPresetCellEntity(Base):
    __tablename__ = "map_preset_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[str] = mapped_column(ForeignKey("map_preset.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    preset: Mapped["MapPresetEntity"] = relationship(back_populates="blocked_cells")


class MapPresetValidCellEntity(Base):
    __tablename__ = "map_preset_valid_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[str] = mapped_column(ForeignKey("map_preset.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    preset: Mapped["MapPresetEntity"] = relationship(back_populates="valid_cells")


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
    valid_cells: Mapped[list["MapProfileValidCellEntity"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="MapProfileValidCellEntity.id",
    )
    topology_nodes: Mapped[list["MapProfileTopologyNodeEntity"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="MapProfileTopologyNodeEntity.id",
    )
    topology_edges: Mapped[list["MapProfileTopologyEdgeEntity"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="MapProfileTopologyEdgeEntity.id",
    )


class MapProfileCellEntity(Base):
    __tablename__ = "map_profile_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("map_profile.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    profile: Mapped["MapProfileEntity"] = relationship(back_populates="blocked_cells")


class MapProfileValidCellEntity(Base):
    __tablename__ = "map_profile_valid_cell"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("map_profile.id"), nullable=False, index=True)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)

    profile: Mapped["MapProfileEntity"] = relationship(back_populates="valid_cells")


class MapProfileTopologyNodeEntity(Base):
    __tablename__ = "map_profile_topology_node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("map_profile.id"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(64), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default="waypoint")

    profile: Mapped["MapProfileEntity"] = relationship(back_populates="topology_nodes")


class MapProfileTopologyEdgeEntity(Base):
    __tablename__ = "map_profile_topology_edge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("map_profile.id"), nullable=False, index=True)
    edge_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    target_key: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="bidirectional")
    lane_type: Mapped[str] = mapped_column(String(32), nullable=False, default="main")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    speed_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    profile: Mapped["MapProfileEntity"] = relationship(back_populates="topology_edges")


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


class AuthUserEntity(Base):
    __tablename__ = "auth_user"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    account_status: Mapped[str] = mapped_column(String(32), nullable=False, default="approved")
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspension_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspended_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suspended_until: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suspended_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deactivated_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deactivated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_login_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    governance_updated_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AuthSessionEntity(Base):
    __tablename__ = "auth_session"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("auth_user.id"), nullable=False, index=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen_at: Mapped[int] = mapped_column(Integer, nullable=False)


class EnterpriseApplicationEntity(Base):
    __tablename__ = "enterprise_application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("auth_user.id"), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    submitted_at: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EnterpriseRequestEntity(Base):
    __tablename__ = "enterprise_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    organization_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    submitter_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submitter_username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submitter_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    submitter_role: Mapped[str] = mapped_column(String(32), nullable=False)
    target_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class PlatformBugFeedbackEntity(Base):
    __tablename__ = "platform_bug_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    submitter_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submitter_username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submitter_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    submitter_role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class ComfyRenderJobEntity(Base):
    __tablename__ = "comfy_render_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    input_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    workflow_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    completed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_urls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    prompt_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)


class ComfyWorkflowTemplateEntity(Base):
    __tablename__ = "comfy_workflow_template"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="organization", index=True)
    organization_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    checkpoint_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    workflow_preset: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_style: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_json_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    workflow_json_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class OperationAuditEntity(Base):
    __tablename__ = "operation_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    operator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_username: Mapped[str] = mapped_column(String(64), nullable=False, default="guest")
    operator_display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Guest")
    operator_role: Mapped[str] = mapped_column(String(32), nullable=False, default="guest")
    performed_at: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)


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
