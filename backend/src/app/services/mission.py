from datetime import UTC, datetime, timedelta
from typing import Callable, Protocol

from app.core.errors import AppError
from app.models import JoinCodeStatus, MissionStatus, RouteKind
from app.models import RouteStepKind as MissionRouteStepKind
from app.repositories.missions import JoinCodeResolution, MissionItemSeed, MissionSeed
from app.schemas.mission import (
    CreateMissionRequest,
    CreateMissionResponse,
    JoinMissionRequest,
    JoinMissionResponse,
    ReturnHomeResponse,
)
from app.security.tokens import generate_join_code, generate_opaque_token, hash_opaque_token

_ROUTE_STEP_KIND_MAP = {
    "STRAIGHT": MissionRouteStepKind.STRAIGHT,
    "LEFT_TURN": MissionRouteStepKind.TURN_LEFT,
    "RIGHT_TURN": MissionRouteStepKind.TURN_RIGHT,
    "CROSSWALK": MissionRouteStepKind.CROSSWALK,
    "ARRIVE": MissionRouteStepKind.ARRIVAL,
}


class MissionRepositoryProtocol(Protocol):
    def create_mission(self, seed: MissionSeed, items: list[MissionItemSeed]): ...

    def get_mission(self, mission_id: str): ...

    def resolve_join_code(
        self,
        join_code: str,
        *,
        now: datetime | None = None,
    ) -> JoinCodeResolution: ...

    def consume_join_code(self, mission_id: str, *, child_token_hash: str) -> bool: ...

    def update_status(
        self, mission_id: str, status: MissionStatus, *, route_kind: RouteKind | None = None
    ): ...


class TmapClientProtocol(Protocol):
    async def get_round_trip(self, home, destination): ...


class MissionService:
    """Create and transition missions without leaking credentials into persistence."""

    def __init__(
        self,
        *,
        repository: MissionRepositoryProtocol,
        tmap_client: TmapClientProtocol,
        join_code_ttl_minutes: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._tmap_client = tmap_client
        self._join_code_ttl_minutes = join_code_ttl_minutes
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create(self, request: CreateMissionRequest) -> CreateMissionResponse:
        routes = await self._tmap_client.get_round_trip(request.home, request.store)
        initial_step = next(
            (step for step in routes.outbound.steps if step.kind.value != "START"),
            None,
        )
        parent_token = generate_opaque_token()
        join_code = generate_join_code()
        join_code_expires_at = self._clock() + timedelta(minutes=self._join_code_ttl_minutes)
        aggregate = self._repository.create_mission(
            MissionSeed(
                home_lat=request.home.latitude,
                home_lng=request.home.longitude,
                store_lat=request.store.latitude,
                store_lng=request.store.longitude,
                outbound_route=routes.outbound.model_dump(mode="json"),
                return_route=routes.returning.model_dump(mode="json"),
                parent_token_hash=hash_opaque_token(parent_token),
                join_code=join_code,
                join_code_expires_at=join_code_expires_at,
                current_step_index=initial_step.index if initial_step is not None else 0,
                current_step_kind=(
                    _ROUTE_STEP_KIND_MAP.get(initial_step.kind.value, MissionRouteStepKind.UNKNOWN)
                    if initial_step is not None
                    else MissionRouteStepKind.UNKNOWN
                ),
            ),
            [
                MissionItemSeed(name=item.name, brand=item.brand, size=item.size)
                for item in request.items
            ],
        )
        return CreateMissionResponse(
            mission_id=aggregate.mission.id,
            join_code=join_code,
            join_code_expires_at=join_code_expires_at.isoformat(),
            parent_token=parent_token,
        )

    def join(self, request: JoinMissionRequest) -> JoinMissionResponse:
        resolution = self._repository.resolve_join_code(request.join_code, now=self._clock())
        if resolution.status is not JoinCodeStatus.ACTIVE or resolution.mission_id is None:
            raise _join_code_error(resolution.status)
        mission_id = resolution.mission_id
        child_token = generate_opaque_token()
        if not self._repository.consume_join_code(
            mission_id, child_token_hash=hash_opaque_token(child_token)
        ):
            raise AppError(
                code="JOIN_CODE_ALREADY_USED",
                message="이미 사용된 참여 코드입니다.",
                status_code=409,
            )
        return JoinMissionResponse(
            mission_id=mission_id,
            child_token=child_token,
            status=MissionStatus.GOING,
            instruction_code="START_OUTBOUND",
            message="마트로 출발해요. 길 안내를 따라가세요.",
        )

    def return_home(self, mission_id: str) -> ReturnHomeResponse:
        mission = self._repository.get_mission(mission_id)
        if mission is None:
            raise AppError(
                code="MISSION_NOT_FOUND", message="미션을 찾을 수 없습니다.", status_code=404
            )
        if mission.status not in (
            MissionStatus.GOING,
            MissionStatus.SHOPPING,
            MissionStatus.RETURNING,
        ):
            raise AppError(
                code="INVALID_STATUS_TRANSITION",
                message="현재 상태에서는 귀가를 시작할 수 없습니다.",
                status_code=409,
            )

        route_kind = _return_route_kind(mission.status, mission.current_route_kind)
        self._repository.update_status(mission_id, MissionStatus.RETURNING, route_kind=route_kind)
        strategy = _return_strategy(route_kind)
        return ReturnHomeResponse(
            status=MissionStatus.RETURNING,
            return_strategy=strategy,
            outbound_progress_m=mission.progress_m,
        )


def _return_route_kind(status: MissionStatus, current_route_kind: RouteKind) -> RouteKind:
    if status is MissionStatus.GOING:
        return RouteKind.OUTBOUND
    if status is MissionStatus.SHOPPING:
        return RouteKind.RETURNING
    return current_route_kind


def _return_strategy(route_kind: RouteKind) -> str:
    return (
        "RETRACE_OUTBOUND_FROM_PROGRESS"
        if route_kind is RouteKind.OUTBOUND
        else "USE_CACHED_RETURN_ROUTE"
    )


def _join_code_error(status: JoinCodeStatus) -> AppError:
    if status is JoinCodeStatus.EXPIRED:
        return AppError(
            code="JOIN_CODE_EXPIRED",
            message="만료된 참여 코드입니다. 새 코드를 받아 주세요.",
            status_code=410,
        )
    if status is JoinCodeStatus.ALREADY_USED:
        return AppError(
            code="JOIN_CODE_ALREADY_USED",
            message="이미 사용된 참여 코드입니다.",
            status_code=409,
        )
    return AppError(
        code="JOIN_CODE_INVALID",
        message="참여 코드를 확인해 주세요.",
        status_code=404,
    )
