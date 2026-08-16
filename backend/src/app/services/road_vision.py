from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.models import MissionEventType, RouteStepKind
from app.schemas.vision.common import RoadVisionResult

ROAD_VISION_LEASE_SECONDS = 10
ROAD_EVENT_DEDUPE_SECONDS = 30
MAX_FRAME_AGE_SECONDS = 10
MAX_FUTURE_FRAME_SECONDS = 5

_CHILD_MESSAGES = {
    RoadVisionResult.STOP: "멈추고 주변을 직접 확인하세요.",
    RoadVisionResult.CAUTION: "주변을 살피고 보호자와 함께 확인하세요.",
    RoadVisionResult.UNKNOWN: "판단할 수 없어요. 멈추고 주변을 직접 확인하세요.",
}


class RoadVisionBusyError(RuntimeError):
    pass


class RoadVisionMissionNotFoundError(LookupError):
    pass


class RoadVisionRepository(Protocol):
    def get_mission(self, mission_id: str) -> object | None: ...

    def acquire_road_vision_lease(
        self, mission_id: str, *, now: datetime, lease_seconds: int
    ) -> bool: ...

    def release_road_vision_lease(
        self, mission_id: str, *, expected_lease_until: datetime
    ) -> bool: ...

    def append_event(
        self,
        mission_id: str,
        event_type: MissionEventType,
        payload: dict[str, str],
        *,
        created_at: datetime,
    ) -> object: ...

    def set_last_road_event_at(self, mission_id: str, occurred_at: datetime) -> object | None: ...


class RoadVisionClient(Protocol):
    async def analyze_road(self, image: bytes) -> object: ...


@dataclass(frozen=True, slots=True)
class RoadVisionEvaluation:
    result: RoadVisionResult
    message: str


class RoadVisionService:
    """Apply conservative road-vision rules without persisting image or model prose."""

    def __init__(
        self, *, repository: RoadVisionRepository, vision_client: RoadVisionClient
    ) -> None:
        self._repository = repository
        self._vision_client = vision_client

    async def evaluate(
        self,
        mission_id: str,
        image: bytes,
        captured_at: datetime,
        *,
        now: datetime | None = None,
    ) -> RoadVisionEvaluation:
        checked_at = _as_utc(now or datetime.now(UTC))
        frame_at = _as_utc(captured_at)
        mission = self._repository.get_mission(mission_id)
        if mission is None:
            raise RoadVisionMissionNotFoundError(mission_id)

        if _is_outside_frame_window(frame_at, checked_at):
            return self._record_and_respond(
                mission_id, mission, RoadVisionResult.UNKNOWN, checked_at
            )

        if not self._repository.acquire_road_vision_lease(
            mission_id, now=checked_at, lease_seconds=ROAD_VISION_LEASE_SECONDS
        ):
            raise RoadVisionBusyError(mission_id)

        lease_until = checked_at + timedelta(seconds=ROAD_VISION_LEASE_SECONDS)
        try:
            try:
                analysis = await self._vision_client.analyze_road(image)
                result = _clamp_result(getattr(analysis, "result", None))
            except Exception:
                result = RoadVisionResult.UNKNOWN

            if getattr(mission, "current_step_kind", None) is RouteStepKind.CROSSWALK:
                result = RoadVisionResult.STOP
            return self._record_and_respond(mission_id, mission, result, checked_at)
        finally:
            self._repository.release_road_vision_lease(mission_id, expected_lease_until=lease_until)

    def _record_and_respond(
        self,
        mission_id: str,
        mission: object,
        result: RoadVisionResult,
        occurred_at: datetime,
    ) -> RoadVisionEvaluation:
        last_event_at = getattr(mission, "last_road_event_at", None)
        if _should_append_event(last_event_at, occurred_at):
            event_type = (
                MissionEventType.ROAD_HAZARD
                if result in (RoadVisionResult.STOP, RoadVisionResult.CAUTION)
                else MissionEventType.VISION_UNAVAILABLE
            )
            self._repository.append_event(
                mission_id,
                event_type,
                {"result": result.value},
                created_at=occurred_at,
            )
            self._repository.set_last_road_event_at(mission_id, occurred_at)
        return RoadVisionEvaluation(result=result, message=_CHILD_MESSAGES[result])


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    return value.astimezone(UTC)


def _is_outside_frame_window(captured_at: datetime, now: datetime) -> bool:
    return captured_at < now - timedelta(
        seconds=MAX_FRAME_AGE_SECONDS
    ) or captured_at > now + timedelta(seconds=MAX_FUTURE_FRAME_SECONDS)


def _clamp_result(value: object) -> RoadVisionResult:
    try:
        return RoadVisionResult(value)
    except (TypeError, ValueError):
        return RoadVisionResult.UNKNOWN


def _should_append_event(last_event_at: datetime | None, now: datetime) -> bool:
    return last_event_at is None or _as_utc(last_event_at) <= now - timedelta(
        seconds=ROAD_EVENT_DEDUPE_SECONDS
    )
