from dataclasses import dataclass
from math import asin, atan2, cos, degrees, radians, sin, sqrt

from app.models import MissionEventType, MissionStatus, RouteKind
from app.models.enums import RouteStepKind as PersistedRouteStepKind
from app.repositories.missions import LocationUpdate, MissionRepository
from app.schemas.navigation.guidance import (
    Guidance,
    InstructionCode,
    LocationRequest,
    LocationResponse,
    VibrationHint,
)
from app.schemas.navigation.route import Coordinate, Route, RoutePoint, RouteStep, RouteStepKind

_EARTH_RADIUS_M = 6_371_000.0
_MAX_RELIABLE_ACCURACY_M = 30.0
_OFF_ROUTE_DISTANCE_M = 30.0
_WRONG_WAY_ANGLE_DEG = 120.0
_ARRIVAL_DISTANCE_M = 30.0
_DEBOUNCE_SAMPLES = 2
_HOME_PROGRESS_EPSILON_M = 1.0


@dataclass(frozen=True, slots=True)
class NavigationEvaluation:
    guidance: Guidance
    step_index: int
    progress_m: float
    off_route_streak: int
    wrong_way_streak: int
    arrival_streak: int
    arrived: bool

    @property
    def instruction_code(self) -> InstructionCode:
        return self.guidance.instruction_code

    @property
    def message(self) -> str:
        return self.guidance.message

    @property
    def vibration_hint(self) -> VibrationHint:
        return self.guidance.vibration_hint

    @property
    def remaining_distance_m(self) -> float:
        return self.guidance.remaining_distance_m

    @property
    def off_route(self) -> bool:
        return self.guidance.off_route

    @property
    def wrong_way(self) -> bool:
        return self.guidance.wrong_way


class NavigationService:
    """Evaluate one GPS sample against an already persisted TMAP route."""

    def evaluate(
        self,
        *,
        route: Route,
        latitude: float,
        longitude: float,
        accuracy_m: float,
        heading_deg: float | None,
        prior_progress_m: float,
        prior_off_route_streak: int,
        prior_wrong_way_streak: int,
        prior_arrival_streak: int,
    ) -> NavigationEvaluation:
        location = Coordinate(latitude=latitude, longitude=longitude)
        nearest_index, progress_m, distance_to_route_m = nearest_route_position(
            route.points, location
        )
        step = next_step(route.steps, progress_m)
        reliable = accuracy_m <= _MAX_RELIABLE_ACCURACY_M

        off_route_streak = _next_streak(
            reliable and distance_to_route_m > _OFF_ROUTE_DISTANCE_M, prior_off_route_streak
        )
        heading_difference = _heading_difference(route.points, nearest_index, heading_deg)
        wrong_way_streak = _next_streak(
            reliable
            and heading_difference is not None
            and heading_difference >= _WRONG_WAY_ANGLE_DEG,
            prior_wrong_way_streak,
        )
        destination_distance_m = haversine_meters(location, route.points[-1])
        arrival_streak = _next_streak(
            reliable and destination_distance_m <= _ARRIVAL_DISTANCE_M, prior_arrival_streak
        )

        off_route = off_route_streak >= _DEBOUNCE_SAMPLES
        wrong_way = wrong_way_streak >= _DEBOUNCE_SAMPLES
        arrived = arrival_streak >= _DEBOUNCE_SAMPLES
        remaining_distance_m = max(0.0, route.total_distance_m - progress_m)
        guidance = _guidance(
            reliable=reliable,
            step=step,
            off_route=off_route,
            wrong_way=wrong_way,
            arrived=arrived,
            remaining_distance_m=remaining_distance_m,
        )
        return NavigationEvaluation(
            guidance=guidance,
            step_index=step.index,
            progress_m=progress_m,
            off_route_streak=off_route_streak,
            wrong_way_streak=wrong_way_streak,
            arrival_streak=arrival_streak,
            arrived=arrived,
        )


class LocationService:
    """Persist cached-route guidance without making a TMAP request per GPS sample."""

    def __init__(
        self, repository: MissionRepository, navigation: NavigationService | None = None
    ) -> None:
        self._repository = repository
        self._navigation = navigation or NavigationService()

    def update(self, mission_id: str, request: LocationRequest) -> LocationResponse:
        mission = self._repository.get_mission(mission_id)
        if mission is None:
            raise LookupError("mission not found")
        if (
            mission.status is MissionStatus.RETURNING
            and mission.current_route_kind is RouteKind.OUTBOUND
            and mission.progress_m <= _HOME_PROGRESS_EPSILON_M
        ):
            zero_progress_response = self._handle_zero_progress_return(mission, request)
            if zero_progress_response is not None:
                return zero_progress_response
        route_kind, route, retracing_outbound = _active_route(mission)
        evaluation = self._navigation.evaluate(
            route=route,
            latitude=request.latitude,
            longitude=request.longitude,
            accuracy_m=request.accuracy_m,
            heading_deg=request.heading_deg,
            prior_progress_m=mission.progress_m,
            prior_off_route_streak=mission.off_route_streak,
            prior_wrong_way_streak=mission.wrong_way_streak,
            prior_arrival_streak=mission.arrival_streak,
        )
        self._append_navigation_events(mission, evaluation)
        updated = self._repository.update_location(
            mission_id,
            LocationUpdate(
                lat=request.latitude,
                lng=request.longitude,
                observed_at=request.observed_at,
                accuracy_m=request.accuracy_m,
                heading_deg=request.heading_deg,
                speed_mps=request.speed_mps,
                route_kind=route_kind,
                step_index=evaluation.step_index,
                step_kind=_persisted_step_kind(_step_for_index(route.steps, evaluation.step_index)),
                progress_m=mission.progress_m if retracing_outbound else evaluation.progress_m,
                off_route_streak=evaluation.off_route_streak,
                wrong_way_streak=evaluation.wrong_way_streak,
                arrival_streak=evaluation.arrival_streak,
            ),
        )
        if updated is None:
            raise LookupError("mission not found")
        status = _advance_arrival(self._repository, updated, evaluation.arrived)
        return LocationResponse(status=status.value, **evaluation.guidance.model_dump())

    def _append_navigation_events(self, mission: object, evaluation: NavigationEvaluation) -> None:
        if mission.off_route_streak < _DEBOUNCE_SAMPLES <= evaluation.off_route_streak:
            self._repository.append_event(mission.id, MissionEventType.OFF_ROUTE)
        if mission.wrong_way_streak < _DEBOUNCE_SAMPLES <= evaluation.wrong_way_streak:
            self._repository.append_event(mission.id, MissionEventType.WRONG_WAY)

    def _handle_zero_progress_return(
        self, mission: object, request: LocationRequest
    ) -> LocationResponse | None:
        location = Coordinate(latitude=request.latitude, longitude=request.longitude)
        home = Coordinate(latitude=mission.home_lat, longitude=mission.home_lng)
        reliable = request.accuracy_m <= _MAX_RELIABLE_ACCURACY_M
        distance_to_home_m = haversine_meters(location, home)
        if reliable and distance_to_home_m <= _ARRIVAL_DISTANCE_M:
            return self._record_home_arrival_sample(mission, request)

        outbound = Route.model_validate(mission.outbound_route)
        _, inferred_progress_m, distance_to_route_m = nearest_route_position(
            outbound.points, location
        )
        if reliable and distance_to_route_m <= _OFF_ROUTE_DISTANCE_M:
            mission.progress_m = max(inferred_progress_m, _HOME_PROGRESS_EPSILON_M + 0.1)
            return None

        updated = self._repository.update_location(
            mission.id,
            LocationUpdate(
                lat=request.latitude,
                lng=request.longitude,
                observed_at=request.observed_at,
                accuracy_m=request.accuracy_m,
                heading_deg=request.heading_deg,
                speed_mps=request.speed_mps,
                route_kind=RouteKind.OUTBOUND,
                step_index=mission.current_step_index,
                step_kind=mission.current_step_kind,
                progress_m=0,
                off_route_streak=0,
                wrong_way_streak=0,
                arrival_streak=0,
            ),
        )
        if updated is None:
            raise LookupError("mission not found")
        return LocationResponse(
            status=MissionStatus.RETURNING.value,
            instruction_code=InstructionCode.LOCATION_UNCERTAIN,
            message="위치를 다시 확인하고 보호자와 함께 이동하세요.",
            vibration_hint=VibrationHint.ALERT,
            remaining_distance_m=distance_to_home_m,
            off_route=False,
            wrong_way=False,
        )

    def _record_home_arrival_sample(
        self, mission: object, request: LocationRequest
    ) -> LocationResponse:
        arrival_streak = mission.arrival_streak + 1
        updated = self._repository.update_location(
            mission.id,
            LocationUpdate(
                lat=request.latitude,
                lng=request.longitude,
                observed_at=request.observed_at,
                accuracy_m=request.accuracy_m,
                heading_deg=request.heading_deg,
                speed_mps=request.speed_mps,
                route_kind=RouteKind.OUTBOUND,
                step_index=mission.current_step_index,
                step_kind=PersistedRouteStepKind.ARRIVAL,
                progress_m=0,
                off_route_streak=0,
                wrong_way_streak=0,
                arrival_streak=arrival_streak,
            ),
        )
        if updated is None:
            raise LookupError("mission not found")
        if arrival_streak >= _DEBOUNCE_SAMPLES:
            status = _advance_arrival(self._repository, updated, arrived=True)
            return LocationResponse(
                status=status.value,
                instruction_code=InstructionCode.ARRIVED,
                message="집에 도착했어요.",
                vibration_hint=VibrationHint.ARRIVAL,
                remaining_distance_m=0,
                off_route=False,
                wrong_way=False,
            )
        return LocationResponse(
            status=MissionStatus.RETURNING.value,
            instruction_code=InstructionCode.CONTINUE,
            message="집 근처에 있어요. 위치를 한 번 더 확인하세요.",
            vibration_hint=VibrationHint.ALERT,
            remaining_distance_m=0,
            off_route=False,
            wrong_way=False,
        )


def haversine_meters(start: Coordinate, end: Coordinate) -> float:
    latitude_delta = radians(end.latitude - start.latitude)
    longitude_delta = radians(end.longitude - start.longitude)
    start_latitude = radians(start.latitude)
    end_latitude = radians(end.latitude)
    value = (
        sin(latitude_delta / 2) ** 2
        + cos(start_latitude) * cos(end_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * asin(sqrt(value))


def bearing_degrees(start: Coordinate, end: Coordinate) -> float:
    longitude_delta = radians(end.longitude - start.longitude)
    start_latitude = radians(start.latitude)
    end_latitude = radians(end.latitude)
    bearing = degrees(
        atan2(
            sin(longitude_delta) * cos(end_latitude),
            cos(start_latitude) * sin(end_latitude)
            - sin(start_latitude) * cos(end_latitude) * cos(longitude_delta),
        )
    )
    return (bearing + 360) % 360


def nearest_route_point(points: tuple[RoutePoint, ...], location: Coordinate) -> tuple[int, float]:
    return min(
        ((index, haversine_meters(location, point)) for index, point in enumerate(points)),
        key=lambda value: value[1],
    )


def nearest_route_position(
    points: tuple[RoutePoint, ...], location: Coordinate
) -> tuple[int, float, float]:
    """Project a location onto route segments to avoid point-only progress jumps."""
    best: tuple[int, float, float] | None = None
    for index, (start, end) in enumerate(zip(points, points[1:])):
        projection = _segment_projection(start, end, location)
        projected_latitude = start.latitude + (end.latitude - start.latitude) * projection
        projected_longitude = start.longitude + (end.longitude - start.longitude) * projection
        distance_m = haversine_meters(
            location, Coordinate(latitude=projected_latitude, longitude=projected_longitude)
        )
        progress_m = start.cumulative_distance_m + projection * (
            end.cumulative_distance_m - start.cumulative_distance_m
        )
        candidate = (index, progress_m, distance_m)
        if best is None or candidate[2] < best[2]:
            best = candidate
    if best is None:
        raise ValueError("route requires at least two points")
    return best


def next_step(steps: tuple[RouteStep, ...], progress_m: float) -> RouteStep:
    maneuvers = tuple(step for step in steps if step.kind is not RouteStepKind.START)
    return next(
        (step for step in maneuvers if step.cumulative_distance_m >= progress_m), maneuvers[-1]
    )


def _heading_difference(
    points: tuple[RoutePoint, ...], nearest_index: int, heading_deg: float | None
) -> float | None:
    if heading_deg is None or nearest_index >= len(points) - 1:
        return None
    expected = bearing_degrees(points[nearest_index], points[nearest_index + 1])
    return abs((heading_deg - expected + 180) % 360 - 180)


def _segment_projection(start: Coordinate, end: Coordinate, location: Coordinate) -> float:
    latitude_scale = 111_320.0
    longitude_scale = latitude_scale * cos(radians((start.latitude + end.latitude) / 2))
    end_x = (end.longitude - start.longitude) * longitude_scale
    end_y = (end.latitude - start.latitude) * latitude_scale
    location_x = (location.longitude - start.longitude) * longitude_scale
    location_y = (location.latitude - start.latitude) * latitude_scale
    length_squared = end_x**2 + end_y**2
    if length_squared == 0:
        return 0.0
    return min(1.0, max(0.0, (location_x * end_x + location_y * end_y) / length_squared))


def _next_streak(condition: bool, prior_streak: int) -> int:
    return prior_streak + 1 if condition else 0


def _guidance(
    *,
    reliable: bool,
    step: RouteStep,
    off_route: bool,
    wrong_way: bool,
    arrived: bool,
    remaining_distance_m: float,
) -> Guidance:
    if not reliable:
        return _make_guidance(
            InstructionCode.LOCATION_UNCERTAIN,
            "위치를 다시 확인하고 보호자와 함께 이동하세요.",
            VibrationHint.ALERT,
            remaining_distance_m,
        )
    if arrived:
        return _make_guidance(
            InstructionCode.ARRIVED, "목적지에 도착했어요.", VibrationHint.ARRIVAL, 0
        )
    if off_route:
        return _make_guidance(
            InstructionCode.OFF_ROUTE,
            "경로에서 벗어났어요. 멈추고 보호자와 함께 위치를 확인하세요.",
            VibrationHint.ALERT,
            remaining_distance_m,
            off_route=True,
            wrong_way=wrong_way,
        )
    if wrong_way:
        return _make_guidance(
            InstructionCode.WRONG_WAY,
            "반대 방향이에요. 멈추고 보호자와 함께 방향을 확인하세요.",
            VibrationHint.ALERT,
            remaining_distance_m,
            wrong_way=True,
        )
    if step.kind is RouteStepKind.CROSSWALK or step.is_crosswalk:
        return _make_guidance(
            InstructionCode.CROSSWALK_STOP,
            "횡단보도 앞이에요. 멈추고 보호자와 함께 주변을 확인하세요.",
            VibrationHint.STOP,
            remaining_distance_m,
        )
    if step.kind is RouteStepKind.LEFT_TURN:
        return _make_guidance(
            InstructionCode.TURN_LEFT,
            "앞에서 왼쪽으로 가세요.",
            VibrationHint.LEFT,
            remaining_distance_m,
        )
    if step.kind is RouteStepKind.RIGHT_TURN:
        return _make_guidance(
            InstructionCode.TURN_RIGHT,
            "앞에서 오른쪽으로 가세요.",
            VibrationHint.RIGHT,
            remaining_distance_m,
        )
    return _make_guidance(
        InstructionCode.CONTINUE, "앞으로 계속 가세요.", VibrationHint.NONE, remaining_distance_m
    )


def _make_guidance(
    instruction_code: InstructionCode,
    message: str,
    vibration_hint: VibrationHint,
    remaining_distance_m: float,
    *,
    off_route: bool = False,
    wrong_way: bool = False,
) -> Guidance:
    return Guidance(
        instruction_code=instruction_code,
        message=message,
        vibration_hint=vibration_hint,
        remaining_distance_m=round(remaining_distance_m, 1),
        off_route=off_route,
        wrong_way=wrong_way,
    )


def _active_route(mission: object) -> tuple[RouteKind, Route, bool]:
    status = getattr(mission, "status")
    if status is MissionStatus.RETURNING:
        outbound = Route.model_validate(getattr(mission, "outbound_route"))
        if getattr(mission, "current_route_kind") is RouteKind.OUTBOUND:
            return (
                RouteKind.OUTBOUND,
                _reverse_outbound_to_progress(outbound, mission.progress_m),
                True,
            )
        return RouteKind.RETURNING, Route.model_validate(getattr(mission, "return_route")), False
    return RouteKind.OUTBOUND, Route.model_validate(getattr(mission, "outbound_route")), False


def _reverse_outbound_to_progress(route: Route, progress_m: float) -> Route:
    """Guide an early return over the travelled outbound section, never via the store."""
    capped_progress = min(max(progress_m, 0.0), route.total_distance_m)
    travelled = [point for point in route.points if point.cumulative_distance_m < capped_progress]
    travelled.append(_point_at_progress(route.points, capped_progress))
    reversed_points = list(reversed(travelled))
    total_distance = capped_progress
    if total_distance <= _HOME_PROGRESS_EPSILON_M:
        raise ValueError("early return route requires travelled distance")
    points = tuple(
        RoutePoint(
            longitude=point.longitude,
            latitude=point.latitude,
            cumulative_distance_m=total_distance - point.cumulative_distance_m,
        )
        for point in reversed_points
    )
    if len(points) < 2:
        points = (
            points[0],
            route.points[0].model_copy(update={"cumulative_distance_m": total_distance}),
        )
    return Route(
        total_distance_m=total_distance,
        total_time_seconds=0,
        points=points,
        steps=_reverse_steps(route.steps, capped_progress, points),
    )


def _point_at_progress(points: tuple[RoutePoint, ...], progress_m: float) -> RoutePoint:
    for start, end in zip(points, points[1:]):
        if start.cumulative_distance_m <= progress_m <= end.cumulative_distance_m:
            span = end.cumulative_distance_m - start.cumulative_distance_m
            ratio = 0.0 if span == 0 else (progress_m - start.cumulative_distance_m) / span
            return RoutePoint(
                longitude=start.longitude + (end.longitude - start.longitude) * ratio,
                latitude=start.latitude + (end.latitude - start.latitude) * ratio,
                cumulative_distance_m=progress_m,
            )
    return points[-1]


def _reverse_steps(
    steps: tuple[RouteStep, ...], progress_m: float, points: tuple[RoutePoint, ...]
) -> tuple[RouteStep, ...]:
    traversed = [step for step in steps if 0 < step.cumulative_distance_m <= progress_m]
    reversed_steps = [
        RouteStep(
            index=index,
            kind=_reverse_step_kind(step.kind),
            coordinate=step.coordinate,
            cumulative_distance_m=progress_m - step.cumulative_distance_m,
            description="",
            is_crosswalk=step.is_crosswalk or step.kind is RouteStepKind.CROSSWALK,
            is_stairs=step.is_stairs,
        )
        for index, step in enumerate(reversed(traversed), start=1)
        if step.kind is not RouteStepKind.ARRIVE
    ]
    return tuple(
        [
            RouteStep(
                index=0, kind=RouteStepKind.START, coordinate=points[0], cumulative_distance_m=0
            ),
            *reversed_steps,
            RouteStep(
                index=len(reversed_steps) + 1,
                kind=RouteStepKind.ARRIVE,
                coordinate=points[-1],
                cumulative_distance_m=progress_m,
            ),
        ]
    )


def _reverse_step_kind(kind: RouteStepKind) -> RouteStepKind:
    if kind is RouteStepKind.LEFT_TURN:
        return RouteStepKind.RIGHT_TURN
    if kind is RouteStepKind.RIGHT_TURN:
        return RouteStepKind.LEFT_TURN
    return kind


def _persisted_step_kind(step: RouteStep) -> PersistedRouteStepKind:
    mapping = {
        RouteStepKind.STRAIGHT: PersistedRouteStepKind.STRAIGHT,
        RouteStepKind.LEFT_TURN: PersistedRouteStepKind.TURN_LEFT,
        RouteStepKind.RIGHT_TURN: PersistedRouteStepKind.TURN_RIGHT,
        RouteStepKind.CROSSWALK: PersistedRouteStepKind.CROSSWALK,
        RouteStepKind.ARRIVE: PersistedRouteStepKind.ARRIVAL,
    }
    return mapping.get(step.kind, PersistedRouteStepKind.UNKNOWN)


def _step_for_index(steps: tuple[RouteStep, ...], index: int) -> RouteStep:
    return next(step for step in steps if step.index == index)


def _advance_arrival(
    repository: MissionRepository, mission: object, arrived: bool
) -> MissionStatus:
    status = getattr(mission, "status")
    if not arrived:
        return status
    if status is MissionStatus.GOING:
        repository.update_status(mission.id, MissionStatus.SHOPPING)
        repository.append_event(mission.id, MissionEventType.ARRIVED_STORE)
        return MissionStatus.SHOPPING
    if status is MissionStatus.RETURNING:
        repository.update_status(mission.id, MissionStatus.COMPLETED)
        repository.append_event(mission.id, MissionEventType.COMPLETED)
        return MissionStatus.COMPLETED
    return status
