from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.errors import AppError
from app.models import MissionStatus
from app.repositories.missions import MissionAggregate
from app.schemas.mission import CreateMissionRequest, JoinMissionRequest
from app.schemas.navigation.route import (
    Coordinate,
    RoundTripRoutes,
    Route,
    RoutePoint,
    RouteStep,
    RouteStepKind,
)
from app.services.mission import MissionService


def _route() -> Route:
    return Route(
        total_distance_m=120,
        total_time_seconds=90,
        points=(
            RoutePoint(longitude=126.97, latitude=37.56, cumulative_distance_m=0),
            RoutePoint(longitude=126.98, latitude=37.57, cumulative_distance_m=120),
        ),
        steps=(
            RouteStep(
                index=0,
                kind=RouteStepKind.START,
                coordinate=Coordinate(longitude=126.97, latitude=37.56),
                cumulative_distance_m=0,
            ),
            RouteStep(
                index=1,
                kind=RouteStepKind.ARRIVE,
                coordinate=Coordinate(longitude=126.98, latitude=37.57),
                cumulative_distance_m=120,
            ),
        ),
    )


@pytest.mark.anyio
async def test_create_fetches_and_persists_round_trip_routes() -> None:
    repository = Mock()
    repository.create_mission.side_effect = lambda seed, items: MissionAggregate(
        mission=type("Mission", (), {"id": "mission-1"})(), items=tuple(items)
    )
    routes = RoundTripRoutes(outbound=_route(), returning=_route())
    tmap = AsyncMock()
    tmap.get_round_trip.return_value = routes
    service = MissionService(repository=repository, tmap_client=tmap, join_code_ttl_minutes=30)

    response = await service.create(
        CreateMissionRequest(
            home=Coordinate(longitude=126.97, latitude=37.56),
            store=Coordinate(longitude=126.98, latitude=37.57),
            items=[{"name": "우유", "brand": "서울우유", "size": "1L"}],
        )
    )

    assert response.mission_id == "mission-1"
    assert len(response.join_code) == 6
    assert response.parent_token
    tmap.get_round_trip.assert_awaited_once()
    seed = repository.create_mission.call_args.args[0]
    assert seed.outbound_route == routes.outbound.model_dump(mode="json")
    assert seed.return_route == routes.returning.model_dump(mode="json")
    assert seed.join_code_expires_at > datetime.now(UTC) + timedelta(minutes=29)


def test_join_consumes_code_once_and_returns_first_instruction() -> None:
    repository = Mock()
    repository.consume_join_code.return_value = True
    repository.get_mission.return_value = type("Mission", (), {"current_step_kind": "UNKNOWN"})()
    service = MissionService(
        repository=repository, tmap_client=AsyncMock(), join_code_ttl_minutes=30
    )
    service._join_code_verifier = type(
        "Verifier", (), {"find_mission_id": lambda *_: "mission-1"}
    )()

    response = service.join(JoinMissionRequest(join_code="123456"))

    assert response.status is MissionStatus.GOING
    assert response.instruction_code == "START_OUTBOUND"
    assert response.child_token
    repository.consume_join_code.assert_called_once()


def test_return_home_allows_going_and_preserves_outbound_progress_for_retrace() -> None:
    repository = Mock()
    repository.get_mission.return_value = type(
        "Mission", (), {"status": MissionStatus.GOING, "progress_m": 84.5}
    )()
    repository.update_status.return_value = type("Mission", (), {})()
    service = MissionService(
        repository=repository, tmap_client=AsyncMock(), join_code_ttl_minutes=30
    )

    response = service.return_home("mission-1")

    assert response.status is MissionStatus.RETURNING
    assert response.return_strategy == "RETRACE_OUTBOUND_FROM_PROGRESS"
    assert response.outbound_progress_m == 84.5
    repository.update_status.assert_called_once_with("mission-1", MissionStatus.RETURNING)


@pytest.mark.parametrize("status", [MissionStatus.WAITING, MissionStatus.COMPLETED])
def test_return_home_rejects_illegal_states(status: MissionStatus) -> None:
    repository = Mock()
    repository.get_mission.return_value = type(
        "Mission", (), {"status": status, "progress_m": 0.0}
    )()
    service = MissionService(
        repository=repository, tmap_client=AsyncMock(), join_code_ttl_minutes=30
    )

    with pytest.raises(AppError) as error:
        service.return_home("mission-1")

    assert error.value.status_code == 409
