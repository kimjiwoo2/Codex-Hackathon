import base64
import binascii
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from sqlalchemy import or_, select, text, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.models import (
    ItemVerdict,
    Mission,
    MissionEvent,
    MissionEventType,
    MissionItem,
    MissionStatus,
    RouteKind,
    RouteStepKind,
)
from app.schemas.common import MissionRole
from app.security.tokens import hash_join_code, is_valid_opaque_token_hash, verify_join_code

_JOIN_CODE_CREATION_LOCK = Lock()
_POSTGRES_JOIN_CODE_LOCK_ID = 4_852_150_684_895_604_553


@dataclass(frozen=True, slots=True)
class MissionItemSeed:
    name: str
    brand: str | None = None
    size: str | None = None


@dataclass(frozen=True, slots=True)
class MissionSeed:
    home_lat: float
    home_lng: float
    store_lat: float
    store_lng: float
    outbound_route: dict[str, Any]
    return_route: dict[str, Any]
    parent_token_hash: str
    join_code: str = field(repr=False)
    join_code_expires_at: datetime


@dataclass(frozen=True, slots=True)
class MissionAggregate:
    mission: Mission
    items: tuple[MissionItem, ...]


@dataclass(frozen=True, slots=True)
class LocationUpdate:
    lat: float
    lng: float
    observed_at: datetime
    accuracy_m: float
    heading_deg: float | None
    speed_mps: float | None
    route_kind: RouteKind
    step_index: int
    step_kind: RouteStepKind
    progress_m: float
    off_route_streak: int
    wrong_way_streak: int
    arrival_streak: int


@dataclass(frozen=True, slots=True)
class ItemVerification:
    verdict: ItemVerdict
    detected_label: str | None
    description: str | None
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class SecretHashCandidate:
    mission_id: str
    encoded_hash: str


class MissionNotFoundError(LookupError):
    pass


class DuplicateJoinCodeError(ValueError):
    pass


class SensitiveEventPayloadError(ValueError):
    pass


class MissionRepository:
    """Transactional persistence boundary for mission aggregates and polling events."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def create_mission(
        self,
        seed: MissionSeed,
        items: Sequence[MissionItemSeed],
    ) -> MissionAggregate:
        if not is_valid_opaque_token_hash(seed.parent_token_hash):
            raise ValueError("parent_token_hash must be a valid opaque-token hash")
        expires_at = _as_utc(seed.join_code_expires_at)
        checked_at = datetime.now(UTC)
        if expires_at <= checked_at:
            raise ValueError("join_code_expires_at must be in the future")

        with _JOIN_CODE_CREATION_LOCK:
            with self._sessions.begin() as session:
                _acquire_join_code_creation_lock(session)
                if _active_join_code_exists(session, seed.join_code, now=checked_at):
                    raise DuplicateJoinCodeError("active join code already exists")
                mission = Mission(
                    home_lat=seed.home_lat,
                    home_lng=seed.home_lng,
                    store_lat=seed.store_lat,
                    store_lng=seed.store_lng,
                    outbound_route=seed.outbound_route,
                    return_route=seed.return_route,
                    parent_token_hash=seed.parent_token_hash,
                    join_code_hash=hash_join_code(seed.join_code),
                    join_code_expires_at=expires_at,
                    items=[
                        MissionItem(
                            ordinal=ordinal,
                            name=item.name,
                            brand=item.brand,
                            size=item.size,
                        )
                        for ordinal, item in enumerate(items)
                    ],
                )
                session.add(mission)
                session.flush()

        return MissionAggregate(mission=mission, items=tuple(mission.items))

    def get_mission(self, mission_id: str) -> Mission | None:
        with self._sessions() as session:
            return session.get(Mission, mission_id)

    def get_aggregate(self, mission_id: str) -> MissionAggregate | None:
        statement = (
            select(Mission).where(Mission.id == mission_id).options(selectinload(Mission.items))
        )
        with self._sessions() as session:
            mission = session.scalar(statement)
            if mission is None:
                return None
            return MissionAggregate(mission=mission, items=tuple(mission.items))

    def update_status(self, mission_id: str, status: MissionStatus) -> Mission | None:
        with self._sessions.begin() as session:
            mission = session.get(Mission, mission_id)
            if mission is None:
                return None
            mission.status = status
            session.flush()
            return mission

    def consume_join_code(
        self,
        mission_id: str,
        *,
        child_token_hash: str,
        now: datetime | None = None,
    ) -> bool:
        if not is_valid_opaque_token_hash(child_token_hash):
            raise ValueError("child_token_hash must be a valid opaque-token hash")
        checked_at = _as_utc(now or datetime.now(UTC))
        statement = (
            update(Mission)
            .where(
                Mission.id == mission_id,
                Mission.status == MissionStatus.WAITING,
                Mission.join_code_hash.is_not(None),
                Mission.join_code_expires_at >= checked_at,
            )
            .values(
                child_token_hash=child_token_hash,
                join_code_hash=None,
                join_code_expires_at=None,
                status=MissionStatus.GOING,
            )
        )
        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def update_location(self, mission_id: str, location: LocationUpdate) -> Mission | None:
        with self._sessions.begin() as session:
            mission = session.get(Mission, mission_id)
            if mission is None:
                return None
            mission.last_lat = location.lat
            mission.last_lng = location.lng
            mission.last_location_at = _as_utc(location.observed_at)
            mission.last_accuracy_m = location.accuracy_m
            mission.last_heading_deg = location.heading_deg
            mission.last_speed_mps = location.speed_mps
            mission.current_route_kind = location.route_kind
            mission.current_step_index = location.step_index
            mission.current_step_kind = location.step_kind
            mission.progress_m = location.progress_m
            mission.off_route_streak = location.off_route_streak
            mission.wrong_way_streak = location.wrong_way_streak
            mission.arrival_streak = location.arrival_streak
            session.flush()
            return mission

    def get_item(self, mission_id: str, item_id: str) -> MissionItem | None:
        statement = select(MissionItem).where(
            MissionItem.id == item_id,
            MissionItem.mission_id == mission_id,
        )
        with self._sessions() as session:
            return session.scalar(statement)

    def update_item_verification(
        self,
        mission_id: str,
        item_id: str,
        verification: ItemVerification,
    ) -> MissionItem | None:
        statement = select(MissionItem).where(
            MissionItem.id == item_id,
            MissionItem.mission_id == mission_id,
        )
        with self._sessions.begin() as session:
            item = session.scalar(statement)
            if item is None:
                return None
            item.last_verdict = verification.verdict
            item.detected_label = verification.detected_label
            item.description = verification.description
            item.verified_at = _as_utc(verification.verified_at)
            session.flush()
            return item

    def append_event(
        self,
        mission_id: str,
        event_type: MissionEventType,
        payload: dict[str, Any] | None = None,
        *,
        created_at: datetime | None = None,
    ) -> MissionEvent:
        normalized_payload = payload or {}
        _reject_sensitive_payload(normalized_payload)
        event = MissionEvent(
            mission_id=mission_id,
            event_type=event_type,
            payload=normalized_payload,
            created_at=_as_utc(created_at or datetime.now(UTC)),
        )
        with self._sessions.begin() as session:
            if session.get(Mission, mission_id) is None:
                raise MissionNotFoundError(mission_id)
            session.add(event)
            session.flush()
        return event

    def list_events(
        self,
        mission_id: str,
        *,
        after_event_id: int = 0,
    ) -> tuple[MissionEvent, ...]:
        statement = (
            select(MissionEvent)
            .where(
                MissionEvent.mission_id == mission_id,
                MissionEvent.id > after_event_id,
            )
            .order_by(MissionEvent.id.asc())
        )
        with self._sessions() as session:
            return tuple(session.scalars(statement))

    def acquire_road_vision_lease(
        self,
        mission_id: str,
        *,
        now: datetime | None = None,
        lease_seconds: int = 10,
    ) -> bool:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        acquired_at = _as_utc(now or datetime.now(UTC))
        lease_until = acquired_at + timedelta(seconds=lease_seconds)
        statement = (
            update(Mission)
            .where(
                Mission.id == mission_id,
                or_(
                    Mission.road_vision_lease_until.is_(None),
                    Mission.road_vision_lease_until <= acquired_at,
                ),
            )
            .values(road_vision_lease_until=lease_until)
        )
        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def release_road_vision_lease(
        self,
        mission_id: str,
        *,
        expected_lease_until: datetime,
    ) -> bool:
        expected_until = _as_utc(expected_lease_until)
        statement = (
            update(Mission)
            .where(
                Mission.id == mission_id,
                Mission.road_vision_lease_until == expected_until,
            )
            .values(road_vision_lease_until=None)
        )
        with self._sessions.begin() as session:
            result = session.execute(statement)
            return result.rowcount == 1

    def set_last_road_event_at(
        self,
        mission_id: str,
        occurred_at: datetime,
    ) -> Mission | None:
        with self._sessions.begin() as session:
            mission = session.get(Mission, mission_id)
            if mission is None:
                return None
            mission.last_road_event_at = _as_utc(occurred_at)
            session.flush()
            return mission

    def find_mission_id_by_role_token_hash(
        self,
        encoded_hash: str,
        role: MissionRole,
    ) -> str | None:
        hash_column = (
            Mission.parent_token_hash if role is MissionRole.PARENT else Mission.child_token_hash
        )
        statement = select(Mission.id).where(hash_column == encoded_hash)
        with self._sessions() as session:
            return session.scalar(statement)

    def list_join_code_candidates(
        self,
        *,
        now: datetime | None = None,
    ) -> tuple[SecretHashCandidate, ...]:
        checked_at = _as_utc(now or datetime.now(UTC))
        statement = select(Mission.id, Mission.join_code_hash).where(
            Mission.status == MissionStatus.WAITING,
            Mission.join_code_hash.is_not(None),
            Mission.join_code_expires_at >= checked_at,
        )
        with self._sessions() as session:
            return tuple(
                SecretHashCandidate(mission_id=mission_id, encoded_hash=encoded_hash)
                for mission_id, encoded_hash in session.execute(statement)
            )

    def delete_mission(self, mission_id: str) -> bool:
        with self._sessions.begin() as session:
            mission = session.get(Mission, mission_id)
            if mission is None:
                return False
            session.delete(mission)
            return True


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timezone-aware datetime is required")
    return value.astimezone(UTC)


def _acquire_join_code_creation_lock(session: Session) -> None:
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _POSTGRES_JOIN_CODE_LOCK_ID},
        )


def _active_join_code_exists(session: Session, join_code: str, *, now: datetime) -> bool:
    statement = select(Mission.join_code_hash).where(
        Mission.status == MissionStatus.WAITING,
        Mission.join_code_hash.is_not(None),
        Mission.join_code_expires_at >= now,
    )
    return any(
        verify_join_code(join_code, encoded_hash) for encoded_hash in session.scalars(statement)
    )


def _reject_sensitive_payload(value: object) -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise SensitiveEventPayloadError("binary material cannot be persisted in events")
    if isinstance(value, str) and value.lstrip().lower().startswith("data:image/"):
        raise SensitiveEventPayloadError("image data URLs cannot be persisted in events")
    if isinstance(value, str) and _looks_like_base64_image(value):
        raise SensitiveEventPayloadError("base64 image material cannot be persisted in events")
    if isinstance(value, dict):
        for child_value in value.values():
            _reject_sensitive_payload(child_value)
    elif isinstance(value, (list, tuple)):
        for child_value in value:
            _reject_sensitive_payload(child_value)


def _looks_like_base64_image(value: str) -> bool:
    compact = "".join(value.split())
    if len(compact) < 16:
        return False
    try:
        decoded = base64.b64decode(compact + "=" * (-len(compact) % 4), validate=True)
    except (binascii.Error, ValueError):
        return False
    return (
        decoded.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a"))
        or len(decoded) >= 12
        and decoded.startswith(b"RIFF")
        and decoded[8:12] == b"WEBP"
    )
