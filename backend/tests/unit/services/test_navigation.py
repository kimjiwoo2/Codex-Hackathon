from datetime import UTC, datetime
from types import SimpleNamespace

from app.models import MissionStatus
from app.schemas.navigation.guidance import InstructionCode, LocationRequest, VibrationHint
from app.schemas.navigation.route import (
    Coordinate,
    Route,
    RoutePoint,
    RouteStep,
    RouteStepKind,
)
from app.services.navigation import LocationService, NavigationService


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


class _RepositoryStub:
    def __init__(self, *, status, outbound_route, return_route, progress_m=0) -> None:
        self.mission = SimpleNamespace(
            id="mission-1",
            status=status,
            outbound_route=outbound_route,
            return_route=return_route,
            progress_m=progress_m,
            off_route_streak=0,
            wrong_way_streak=0,
            arrival_streak=0,
        )
        self.location_updates = []

    def get_mission(self, mission_id):
        return self.mission if mission_id == self.mission.id else None

    def update_location(self, mission_id, location):
        self.location_updates.append(location)
        return self.mission

    def update_status(self, mission_id, status):
        self.mission.status = status
        return self.mission

    def append_event(self, *args, **kwargs):
        return None
