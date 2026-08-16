from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.models import MissionStatus, RouteKind
from app.repositories import MissionAggregate
from app.schemas.parent import (
    ParentEvent,
    ParentItem,
    ParentLocation,
    ParentSnapshotResponse,
)

LOCATION_STALE_AFTER_SECONDS = 15


class ParentSnapshotNotFoundError(LookupError):
    """Raised when a parent asks for a mission that no longer exists."""


class ParentSnapshotRepository(Protocol):
    def get_aggregate(self, mission_id: str) -> MissionAggregate | None: ...

    def list_events(self, mission_id: str, *, after_event_id: int) -> tuple[object, ...]: ...


class ParentSnapshotService:
    """Build a polling response from persisted state without changing that state."""

    def __init__(self, repository: ParentSnapshotRepository) -> None:
        self._repository = repository

    def get_snapshot(
        self,
        mission_id: str,
        *,
        after_event_id: int = 0,
        now: datetime | None = None,
    ) -> ParentSnapshotResponse:
        aggregate = self._repository.get_aggregate(mission_id)
        if aggregate is None:
            raise ParentSnapshotNotFoundError(mission_id)

        checked_at = _as_utc(now or datetime.now(UTC))
        mission = aggregate.mission
        events = self._repository.list_events(mission_id, after_event_id=after_event_id)
        location = _location_from(mission)
        return ParentSnapshotResponse(
            mission_id=mission.id,
            status=mission.status,
            location=location,
            location_stale=_is_location_stale(
                getattr(mission, "last_location_at", None), checked_at
            ),
            remaining_distance_m=_remaining_distance(mission),
            items=tuple(
                ParentItem(
                    item_id=item.id,
                    name=item.name,
                    verdict=item.last_verdict,
                    detected_label=item.detected_label,
                    verified_at=item.verified_at,
                )
                for item in aggregate.items
            ),
            events=tuple(
                ParentEvent(
                    event_id=event.id,
                    event_type=event.event_type,
                    payload=event.payload,
                    created_at=event.created_at,
                )
                for event in events
            ),
            next_event_id=events[-1].id if events else after_event_id,
        )


def _location_from(mission: object) -> ParentLocation | None:
    latitude = getattr(mission, "last_lat", None)
    longitude = getattr(mission, "last_lng", None)
    observed_at = getattr(mission, "last_location_at", None)
    if latitude is None or longitude is None or observed_at is None:
        return None
    return ParentLocation(
        latitude=latitude,
        longitude=longitude,
        observed_at=observed_at,
        accuracy_m=getattr(mission, "last_accuracy_m", None),
    )


def _remaining_distance(mission: object) -> float:
    progress_m = float(getattr(mission, "progress_m", 0.0))
    if (
        getattr(mission, "status") is MissionStatus.RETURNING
        and getattr(mission, "current_route_kind") is RouteKind.OUTBOUND
    ):
        return round(max(0.0, progress_m), 1)

    route = (
        getattr(mission, "return_route")
        if getattr(mission, "current_route_kind") is RouteKind.RETURNING
        else getattr(mission, "outbound_route")
    )
    total_distance = route.get("totalDistanceM", route.get("total_distance_m", 0.0))
    try:
        return round(max(0.0, float(total_distance) - progress_m), 1)
    except (TypeError, ValueError):
        return 0.0


def _is_location_stale(last_location_at: datetime | None, now: datetime) -> bool:
    return last_location_at is None or _as_utc(last_location_at) <= now - timedelta(
        seconds=LOCATION_STALE_AFTER_SECONDS
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("location timestamps must be timezone-aware")
    return value.astimezone(UTC)
