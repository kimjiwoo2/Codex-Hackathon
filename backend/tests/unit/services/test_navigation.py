from datetime import UTC, datetime
from types import SimpleNamespace

from app.models import MissionEventType, MissionStatus, RouteKind
from app.models import RouteStepKind as PersistedRouteStepKind
from app.schemas.navigation.guidance import InstructionCode, LocationRequest, VibrationHint
from app.schemas.navigation.route import (
    Coordinate,
    Route,
    RoutePoint,
    RouteStep,
    RouteStepKind,
)
from app.services.navigation import (
    LocationService,
    NavigationService,
    _reverse_outbound_to_progress,
)


def _route(*, crosswalk: bool = False) -> Route:
    return Route(
        total_distance_m=200,
        total_time_seconds=120,
        points=(
            RoutePoint(longitude=126.0, latitude=37.0, cumulative_distance_m=0),
            RoutePoint(longitude=126.001, latitude=37.0, cumulative_distance_m=100),
            RoutePoint(longitude=126.002, latitude=37.0, cumulative_distance_m=200),
        ),
        steps=(
            RouteStep(
                index=0,
                kind=RouteStepKind.START,
                coordinate=Coordinate(longitude=126.0, latitude=37.0),
                cumulative_distance_m=0,
            ),
            RouteStep(
                index=1,
                kind=RouteStepKind.CROSSWALK if crosswalk else RouteStepKind.LEFT_TURN,
                coordinate=Coordinate(longitude=126.001, latitude=37.0),
                cumulative_distance_m=100,
            ),
            RouteStep(
                index=2,
                kind=RouteStepKind.ARRIVE,
                coordinate=Coordinate(longitude=126.002, latitude=37.0),
                cumulative_distance_m=200,
            ),
        ),
    )


def test_returns_fixed_turn_guidance_from_cached_route() -> None:
    result = NavigationService().evaluate(
        route=_route(),
        latitude=37.0,
        longitude=126.0001,
        accuracy_m=8,
        heading_deg=90,
        prior_progress_m=0,
        prior_off_route_streak=0,
        prior_wrong_way_streak=0,
        prior_arrival_streak=0,
    )

    assert result.instruction_code is InstructionCode.TURN_LEFT
    assert result.vibration_hint is VibrationHint.LEFT
    assert result.off_route is False
    assert result.wrong_way is False
    assert 0 < result.remaining_distance_m < 200


def test_crosswalk_overrides_other_maneuver_with_stop_guidance() -> None:
    result = NavigationService().evaluate(
        route=_route(crosswalk=True),
        latitude=37.0,
        longitude=126.001,
        accuracy_m=5,
        heading_deg=90,
        prior_progress_m=90,
        prior_off_route_streak=0,
        prior_wrong_way_streak=0,
        prior_arrival_streak=0,
    )

    assert result.instruction_code is InstructionCode.CROSSWALK_STOP
    assert result.vibration_hint is VibrationHint.STOP
    assert "건너" not in result.message


def test_wrong_way_and_off_route_require_two_accurate_samples() -> None:
    service = NavigationService()
    first = service.evaluate(
        route=_route(),
        latitude=37.001,
        longitude=126.0002,
        accuracy_m=5,
        heading_deg=270,
        prior_progress_m=80,
        prior_off_route_streak=0,
        prior_wrong_way_streak=0,
        prior_arrival_streak=0,
    )
    second = service.evaluate(
        route=_route(),
        latitude=37.001,
        longitude=126.0002,
        accuracy_m=5,
        heading_deg=270,
        prior_progress_m=80,
        prior_off_route_streak=first.off_route_streak,
        prior_wrong_way_streak=first.wrong_way_streak,
        prior_arrival_streak=0,
    )

    assert first.wrong_way is False
    assert first.wrong_way_streak == 1
    assert second.off_route is True
    assert second.wrong_way is True
    assert second.instruction_code is InstructionCode.OFF_ROUTE


def test_poor_accuracy_neither_advances_safety_streaks_nor_declares_wrong_way() -> None:
    result = NavigationService().evaluate(
        route=_route(),
        latitude=37.0,
        longitude=126.01,
        accuracy_m=31,
        heading_deg=270,
        prior_progress_m=80,
        prior_off_route_streak=1,
        prior_wrong_way_streak=1,
        prior_arrival_streak=1,
    )

    assert result.off_route_streak == 0
    assert result.wrong_way_streak == 0
    assert result.arrival_streak == 0
    assert result.instruction_code is InstructionCode.LOCATION_UNCERTAIN


def test_arrival_requires_two_accurate_samples() -> None:
    first = NavigationService().evaluate(
        route=_route(),
        latitude=37.0,
        longitude=126.002,
        accuracy_m=5,
        heading_deg=90,
        prior_progress_m=180,
        prior_off_route_streak=0,
        prior_wrong_way_streak=0,
        prior_arrival_streak=0,
    )
    second = NavigationService().evaluate(
        route=_route(),
        latitude=37.0,
        longitude=126.002,
        accuracy_m=5,
        heading_deg=90,
        prior_progress_m=180,
        prior_off_route_streak=0,
        prior_wrong_way_streak=0,
        prior_arrival_streak=first.arrival_streak,
    )

    assert first.arrived is False
    assert second.arrived is True
    assert second.instruction_code is InstructionCode.ARRIVED


def test_location_service_uses_return_route_only_after_returning_status() -> None:
    repository = _RepositoryStub(
        status=MissionStatus.RETURNING,
        outbound_route=_route().model_dump(mode="json"),
        return_route=_route().model_dump(mode="json"),
        progress_m=100,
        current_route_kind=RouteKind.RETURNING,
    )
    response = LocationService(repository).update(
        "mission-1",
        LocationRequest(
            latitude=37.0,
            longitude=126.002,
            accuracy_m=5,
            heading_deg=90,
            observed_at=datetime.now(UTC),
        ),
    )

    assert response.status == "RETURNING"
    assert repository.location_updates[0].route_kind.value == "RETURNING"


def test_early_return_at_zero_progress_completes_at_home_without_route_validation_error() -> None:
    repository = _RepositoryStub(
        status=MissionStatus.RETURNING,
        outbound_route=_route().model_dump(mode="json"),
        return_route=_route().model_dump(mode="json"),
        progress_m=0,
    )

    response = LocationService(repository).update(
        "mission-1",
        LocationRequest(
            latitude=37.0,
            longitude=126.0,
            accuracy_m=5,
            heading_deg=90,
            observed_at=datetime.now(UTC),
        ),
    )

    assert response.status == "COMPLETED"
    assert response.instruction_code is InstructionCode.ARRIVED
    assert repository.location_updates[0].step_kind is PersistedRouteStepKind.ARRIVAL


def test_early_return_preserves_crosswalk_for_stop_guidance_and_persistence() -> None:
    repository = _RepositoryStub(
        status=MissionStatus.RETURNING,
        outbound_route=_route(crosswalk=True).model_dump(mode="json"),
        return_route=_route().model_dump(mode="json"),
        progress_m=100,
    )

    response = LocationService(repository).update(
        "mission-1",
        LocationRequest(
            latitude=37.0,
            longitude=126.001,
            accuracy_m=5,
            heading_deg=270,
            observed_at=datetime.now(UTC),
        ),
    )

    assert response.instruction_code is InstructionCode.CROSSWALK_STOP
    assert repository.location_updates[0].step_kind is PersistedRouteStepKind.CROSSWALK
    assert repository.location_updates[0].route_kind.value == "OUTBOUND"


def test_reverse_outbound_preserves_steps_and_swaps_turn_directions() -> None:
    outbound = _route().model_copy(
        update={
            "steps": (
                RouteStep(
                    index=0,
                    kind=RouteStepKind.START,
                    coordinate=Coordinate(longitude=126.0, latitude=37.0),
                    cumulative_distance_m=0,
                ),
                RouteStep(
                    index=1,
                    kind=RouteStepKind.RIGHT_TURN,
                    coordinate=Coordinate(longitude=126.0005, latitude=37.0),
                    cumulative_distance_m=50,
                ),
                RouteStep(
                    index=2,
                    kind=RouteStepKind.LEFT_TURN,
                    coordinate=Coordinate(longitude=126.001, latitude=37.0),
                    cumulative_distance_m=100,
                ),
                RouteStep(
                    index=3,
                    kind=RouteStepKind.ARRIVE,
                    coordinate=Coordinate(longitude=126.002, latitude=37.0),
                    cumulative_distance_m=200,
                ),
            )
        }
    )

    reversed_route = _reverse_outbound_to_progress(outbound, 150)

    assert [step.kind for step in reversed_route.steps] == [
        RouteStepKind.START,
        RouteStepKind.RIGHT_TURN,
        RouteStepKind.LEFT_TURN,
        RouteStepKind.ARRIVE,
    ]


def test_off_route_and_wrong_way_events_are_emitted_once_at_debounce_threshold() -> None:
    repository = _RepositoryStub(
        status=MissionStatus.GOING,
        outbound_route=_route().model_dump(mode="json"),
        return_route=_route().model_dump(mode="json"),
    )
    repository.mission.off_route_streak = 1
    repository.mission.wrong_way_streak = 1
    service = LocationService(repository)
    request = LocationRequest(
        latitude=37.001,
        longitude=126.0002,
        accuracy_m=5,
        heading_deg=270,
        observed_at=datetime.now(UTC),
    )

    service.update("mission-1", request)
    service.update("mission-1", request)

    assert repository.events == [MissionEventType.OFF_ROUTE, MissionEventType.WRONG_WAY]


class _RepositoryStub:
    def __init__(
        self,
        *,
        status,
        outbound_route,
        return_route,
        progress_m=0,
        current_route_kind=RouteKind.OUTBOUND,
    ) -> None:
        self.mission = SimpleNamespace(
            id="mission-1",
            status=status,
            outbound_route=outbound_route,
            return_route=return_route,
            current_route_kind=current_route_kind,
            progress_m=progress_m,
            off_route_streak=0,
            wrong_way_streak=0,
            arrival_streak=0,
        )
        self.location_updates = []
        self.events = []

    def get_mission(self, mission_id):
        return self.mission if mission_id == self.mission.id else None

    def update_location(self, mission_id, location):
        self.location_updates.append(location)
        self.mission.current_route_kind = location.route_kind
        self.mission.progress_m = location.progress_m
        self.mission.off_route_streak = location.off_route_streak
        self.mission.wrong_way_streak = location.wrong_way_streak
        self.mission.arrival_streak = location.arrival_streak
        return self.mission

    def update_status(self, mission_id, status):
        self.mission.status = status
        return self.mission

    def append_event(self, _mission_id, event_type, *args, **kwargs):
        self.events.append(event_type)
        return None
