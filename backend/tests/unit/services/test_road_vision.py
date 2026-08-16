from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from app.integrations.openai.client import VisionUnavailable
from app.models import MissionEventType, RouteStepKind
from app.schemas.vision.common import RoadVisionAnalysis, RoadVisionResult
from app.services.road_vision import RoadVisionBusyError, RoadVisionService


def _mission(*, step_kind: RouteStepKind = RouteStepKind.UNKNOWN, last_event_at=None):
    return SimpleNamespace(current_step_kind=step_kind, last_road_event_at=last_event_at)


def _service(*, mission, analysis=None, acquire=True):
    repository = Mock()
    repository.get_mission.return_value = mission
    repository.acquire_road_vision_lease.return_value = acquire
    client = AsyncMock()
    client.analyze_road.return_value = analysis
    return RoadVisionService(repository=repository, vision_client=client), repository, client


@pytest.mark.anyio
async def test_unsafe_model_result_is_clamped_and_description_is_never_exposed() -> None:
    service, repository, _ = _service(
        mission=_mission(),
        analysis=SimpleNamespace(result="CROSS_OK", description="건너도 됩니다"),
    )

    result = await service.evaluate("mission-1", b"\xff\xd8jpeg\xff\xd9", datetime.now(UTC))

    assert result.result is RoadVisionResult.UNKNOWN
    assert result.message == "판단할 수 없어요. 멈추고 주변을 직접 확인하세요."
    assert "건너" not in result.message
    repository.append_event.assert_called_once_with(
        "mission-1", MissionEventType.VISION_UNAVAILABLE, {"result": "UNKNOWN"}, created_at=ANY
    )


@pytest.mark.anyio
async def test_crosswalk_always_returns_stop_even_when_model_returns_caution() -> None:
    analysis = RoadVisionAnalysis(result=RoadVisionResult.CAUTION, description="차량이 보입니다")
    service, repository, _ = _service(
        mission=_mission(step_kind=RouteStepKind.CROSSWALK), analysis=analysis
    )

    result = await service.evaluate("mission-1", b"jpeg", datetime.now(UTC))

    assert result.result is RoadVisionResult.STOP
    assert result.message == "멈추고 주변을 직접 확인하세요."
    repository.append_event.assert_called_once_with(
        "mission-1", MissionEventType.ROAD_HAZARD, {"result": "STOP"}, created_at=ANY
    )


@pytest.mark.anyio
@pytest.mark.parametrize("offset", [timedelta(seconds=-11), timedelta(seconds=6)])
async def test_stale_or_future_frame_skips_openai_and_returns_unknown(offset) -> None:
    now = datetime.now(UTC)
    service, repository, client = _service(mission=_mission())

    result = await service.evaluate("mission-1", b"jpeg", now + offset, now=now)

    assert result.result is RoadVisionResult.UNKNOWN
    client.analyze_road.assert_not_awaited()
    repository.acquire_road_vision_lease.assert_not_called()


@pytest.mark.anyio
async def test_busy_lease_does_not_call_vision_adapter() -> None:
    service, _, client = _service(mission=_mission(), acquire=False)

    with pytest.raises(RoadVisionBusyError):
        await service.evaluate("mission-1", b"jpeg", datetime.now(UTC))

    client.analyze_road.assert_not_awaited()


@pytest.mark.anyio
async def test_vision_unavailable_becomes_unknown_and_releases_lease() -> None:
    now = datetime.now(UTC)
    service, repository, client = _service(mission=_mission())
    client.analyze_road.side_effect = VisionUnavailable()

    result = await service.evaluate("mission-1", b"jpeg", now, now=now)

    assert result.result is RoadVisionResult.UNKNOWN
    repository.append_event.assert_called_once_with(
        "mission-1", MissionEventType.VISION_UNAVAILABLE, {"result": "UNKNOWN"}, created_at=ANY
    )
    repository.release_road_vision_lease.assert_called_once()


@pytest.mark.anyio
async def test_unexpected_vision_error_propagates_and_releases_lease() -> None:
    now = datetime.now(UTC)
    service, repository, client = _service(
        mission=_mission(last_event_at=now - timedelta(seconds=10))
    )
    client.analyze_road.side_effect = RuntimeError("adapter failure")

    with pytest.raises(RuntimeError, match="adapter failure"):
        await service.evaluate("mission-1", b"jpeg", now, now=now)

    repository.append_event.assert_not_called()
    repository.set_last_road_event_at.assert_not_called()
    repository.release_road_vision_lease.assert_called_once()
