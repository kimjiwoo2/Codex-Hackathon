from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models import ItemVerdict, MissionEventType, MissionStatus, RouteKind
from app.repositories import MissionAggregate
from app.services.parent_snapshot import ParentSnapshotNotFoundError, ParentSnapshotService


def _aggregate(*, last_location_at=None, route_kind=RouteKind.OUTBOUND) -> MissionAggregate:
    mission = SimpleNamespace(
        id="mission-1",
        status=MissionStatus.GOING,
        last_lat=37.56,
        last_lng=126.97,
        last_location_at=last_location_at,
        last_accuracy_m=8.0,
        current_route_kind=route_kind,
        progress_m=35.4,
        outbound_route={"totalDistanceM": 120},
        return_route={"totalDistanceM": 80},
    )
    item = SimpleNamespace(
        id="item-1",
        name="우유",
        last_verdict=ItemVerdict.MATCH,
        detected_label="서울우유 1L",
        verified_at=datetime(2026, 8, 16, tzinfo=UTC),
    )
    return MissionAggregate(mission=mission, items=(item,))


def _event(event_id: int):
    return SimpleNamespace(
        id=event_id,
        event_type=MissionEventType.ROAD_HAZARD,
        payload={"result": "STOP"},
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
    )


def test_snapshot_combines_location_status_remaining_items_and_new_events() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    repository = Mock()
    repository.get_aggregate.return_value = _aggregate(last_location_at=now - timedelta(seconds=2))
    repository.list_events.return_value = (_event(4), _event(7))

    snapshot = ParentSnapshotService(repository).get_snapshot(
        "mission-1", after_event_id=3, now=now
    )

    assert snapshot.status is MissionStatus.GOING
    assert snapshot.location is not None
    assert snapshot.location.latitude == 37.56
    assert snapshot.remaining_distance_m == 84.6
    assert snapshot.items[0].verdict is ItemVerdict.MATCH
    assert [event.event_id for event in snapshot.events] == [4, 7]
    assert snapshot.next_event_id == 7
    assert not snapshot.location_stale
    repository.list_events.assert_called_once_with("mission-1", after_event_id=3)


def test_snapshot_keeps_cursor_when_no_new_events_and_never_mutates_polling_state() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    repository = Mock()
    repository.get_aggregate.return_value = _aggregate(last_location_at=now - timedelta(seconds=20))
    repository.list_events.return_value = ()

    snapshot = ParentSnapshotService(repository).get_snapshot(
        "mission-1", after_event_id=7, now=now
    )

    assert snapshot.events == ()
    assert snapshot.next_event_id == 7
    assert snapshot.location_stale
    assert [call.args[0] for call in repository.method_calls] == ["mission-1", "mission-1"]


def test_snapshot_marks_missing_location_stale_and_uses_return_route_distance() -> None:
    repository = Mock()
    repository.get_aggregate.return_value = _aggregate(route_kind=RouteKind.RETURNING)
    repository.get_aggregate.return_value.mission.last_lat = None
    repository.get_aggregate.return_value.mission.last_lng = None
    repository.get_aggregate.return_value.mission.last_location_at = None
    repository.list_events.return_value = ()

    snapshot = ParentSnapshotService(repository).get_snapshot("mission-1", now=datetime.now(UTC))

    assert snapshot.location is None
    assert snapshot.location_stale
    assert snapshot.remaining_distance_m == 44.6


def test_snapshot_rejects_unknown_mission() -> None:
    repository = Mock()
    repository.get_aggregate.return_value = None

    with pytest.raises(ParentSnapshotNotFoundError):
        ParentSnapshotService(repository).get_snapshot("missing")
