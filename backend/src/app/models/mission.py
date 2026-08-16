from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UtcDateTime
from app.models.enums import (
    ItemVerdict,
    MissionEventType,
    MissionStatus,
    RouteKind,
    RouteStepKind,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _enum(enum_type: type, *, name: str) -> Enum:
    return Enum(enum_type, name=name, native_enum=False, validate_strings=True)


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[MissionStatus] = mapped_column(
        _enum(MissionStatus, name="mission_status"), default=MissionStatus.WAITING, nullable=False
    )

    parent_token_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    child_token_hash: Mapped[str | None] = mapped_column(String(256), unique=True)
    join_code_hash: Mapped[str | None] = mapped_column(String(256))
    join_code_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime())

    home_lat: Mapped[float] = mapped_column(Float, nullable=False)
    home_lng: Mapped[float] = mapped_column(Float, nullable=False)
    store_lat: Mapped[float] = mapped_column(Float, nullable=False)
    store_lng: Mapped[float] = mapped_column(Float, nullable=False)
    outbound_route: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    return_route: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    last_lat: Mapped[float | None] = mapped_column(Float)
    last_lng: Mapped[float | None] = mapped_column(Float)
    last_location_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    last_accuracy_m: Mapped[float | None] = mapped_column(Float)
    last_heading_deg: Mapped[float | None] = mapped_column(Float)
    last_speed_mps: Mapped[float | None] = mapped_column(Float)

    current_route_kind: Mapped[RouteKind] = mapped_column(
        _enum(RouteKind, name="route_kind"), default=RouteKind.OUTBOUND, nullable=False
    )
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step_kind: Mapped[RouteStepKind] = mapped_column(
        _enum(RouteStepKind, name="route_step_kind"),
        default=RouteStepKind.UNKNOWN,
        nullable=False,
    )
    progress_m: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    off_route_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_way_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    arrival_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_road_event_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    road_vision_lease_until: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    items: Mapped[list["MissionItem"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionItem.ordinal",
    )
    events: Mapped[list["MissionEvent"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionEvent.id",
    )


class MissionItem(Base):
    __tablename__ = "mission_items"
    __table_args__ = (
        Index("ix_mission_items_mission_ordinal", "mission_id", "ordinal", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[str | None] = mapped_column(String(100))
    last_verdict: Mapped[ItemVerdict] = mapped_column(
        _enum(ItemVerdict, name="item_verdict"), default=ItemVerdict.UNKNOWN, nullable=False
    )
    detected_label: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=_utc_now, nullable=False)

    mission: Mapped[Mission] = relationship(back_populates="items")


class MissionEvent(Base):
    __tablename__ = "mission_events"
    __table_args__ = (Index("ix_mission_events_mission_id_id", "mission_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[MissionEventType] = mapped_column(
        _enum(MissionEventType, name="mission_event_type"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=_utc_now, nullable=False)

    mission: Mapped[Mission] = relationship(back_populates="events")
