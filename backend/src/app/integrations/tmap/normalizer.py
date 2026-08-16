from collections.abc import Mapping, Sequence
from math import asin, cos, radians, sin, sqrt
from typing import Any

from pydantic import ValidationError

from app.integrations.tmap.errors import TmapUnavailable
from app.schemas.navigation.route import (
    Coordinate,
    Route,
    RoutePoint,
    RouteStep,
    RouteStepKind,
)

_CROSSWALK_TURN_TYPES = frozenset(range(211, 218))

_TURN_STEP_KINDS = {
    11: RouteStepKind.STRAIGHT,
    12: RouteStepKind.LEFT_TURN,
    13: RouteStepKind.RIGHT_TURN,
    14: RouteStepKind.U_TURN,
    16: RouteStepKind.LEFT_TURN,
    17: RouteStepKind.LEFT_TURN,
    18: RouteStepKind.RIGHT_TURN,
    19: RouteStepKind.RIGHT_TURN,
    125: RouteStepKind.OVERPASS,
    126: RouteStepKind.UNDERPASS,
    127: RouteStepKind.STAIRS,
    128: RouteStepKind.RAMP,
    129: RouteStepKind.STAIRS,
    200: RouteStepKind.START,
    201: RouteStepKind.ARRIVE,
    218: RouteStepKind.ELEVATOR,
    233: RouteStepKind.STRAIGHT,
}

_FACILITY_STEP_KINDS = {
    12: RouteStepKind.OVERPASS,
    14: RouteStepKind.UNDERPASS,
    15: RouteStepKind.CROSSWALK,
    17: RouteStepKind.STAIRS,
}


def normalize_route(payload: Mapping[str, Any]) -> Route:
    """Convert a TMAP pedestrian GeoJSON response into the internal route contract."""
    try:
        features = _sorted_features(payload)
        route_points: list[RoutePoint] = []
        steps: list[RouteStep] = []
        cumulative_distance = 0.0
        total_time = 0
        provider_total_distance: float | None = None
        provider_total_time: int | None = None
        line_count = 0

        for feature in features:
            geometry = _mapping(feature.get("geometry"))
            properties = _mapping(feature.get("properties"))
            geometry_type = geometry.get("type")

            if geometry_type == "Point":
                coordinate = _coordinate(geometry.get("coordinates"))
                _append_point_if_new(route_points, coordinate, cumulative_distance)

                turn_type = _optional_int(properties.get("turnType"))
                if turn_type == 200:
                    provider_total_distance = _optional_float(properties.get("totalDistance"))
                    provider_total_time = _optional_int(properties.get("totalTime"))

                steps.append(
                    _turn_step(
                        index=len(steps),
                        coordinate=coordinate,
                        cumulative_distance=cumulative_distance,
                        turn_type=turn_type,
                        description=str(properties.get("description", "")),
                    )
                )
                continue

            if geometry_type != "LineString":
                continue

            coordinates = _line_coordinates(geometry.get("coordinates"))
            segment_distance = _non_negative_float(properties.get("distance", 0))
            segment_start_distance = cumulative_distance
            _append_segment_points(
                route_points,
                coordinates,
                segment_start_distance,
                segment_distance,
            )
            cumulative_distance += segment_distance
            total_time += _non_negative_int(properties.get("time", 0))
            line_count += 1

            facility_type = _optional_int(properties.get("facilityType"))
            facility_kind = _FACILITY_STEP_KINDS.get(facility_type)
            if facility_kind is not None:
                steps.append(
                    RouteStep(
                        index=len(steps),
                        kind=facility_kind,
                        coordinate=coordinates[0],
                        cumulative_distance_m=segment_start_distance,
                        description=str(properties.get("description", "")),
                        facility_type=facility_type,
                        is_crosswalk=facility_kind is RouteStepKind.CROSSWALK,
                        is_stairs=facility_kind is RouteStepKind.STAIRS,
                    )
                )

        if line_count == 0 or cumulative_distance <= 0 or len(route_points) < 2:
            raise ValueError("TMAP returned no usable pedestrian geometry")

        total_distance = provider_total_distance or cumulative_distance
        scale = total_distance / cumulative_distance
        normalized_points = tuple(
            point.model_copy(update={"cumulative_distance_m": point.cumulative_distance_m * scale})
            for point in route_points
        )
        normalized_steps = tuple(
            step.model_copy(update={"cumulative_distance_m": step.cumulative_distance_m * scale})
            for step in steps
        )

        return Route(
            total_distance_m=total_distance,
            total_time_seconds=provider_total_time
            if provider_total_time is not None
            else total_time,
            points=normalized_points,
            steps=normalized_steps,
        )
    except TmapUnavailable:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise TmapUnavailable() from error


def _sorted_features(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("invalid GeoJSON type")
    raw_features = payload.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise ValueError("missing GeoJSON features")

    features = [_mapping(feature) for feature in raw_features]
    return sorted(features, key=lambda feature: _feature_index(feature))


def _feature_index(feature: Mapping[str, Any]) -> int:
    properties = _mapping(feature.get("properties"))
    return int(properties.get("index", 0))


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("expected object")
    return value


def _coordinate(value: object) -> Coordinate:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 2:
        raise TypeError("invalid coordinate")
    return Coordinate(longitude=float(value[0]), latitude=float(value[1]))


def _line_coordinates(value: object) -> tuple[Coordinate, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError("invalid line geometry")
    coordinates = tuple(_coordinate(item) for item in value)
    if len(coordinates) < 2:
        raise ValueError("line geometry requires at least two coordinates")
    return coordinates


def _turn_step(
    *,
    index: int,
    coordinate: Coordinate,
    cumulative_distance: float,
    turn_type: int | None,
    description: str,
) -> RouteStep:
    if turn_type in _CROSSWALK_TURN_TYPES:
        kind = RouteStepKind.CROSSWALK
    else:
        kind = _TURN_STEP_KINDS.get(turn_type, RouteStepKind.OTHER)
    return RouteStep(
        index=index,
        kind=kind,
        coordinate=coordinate,
        cumulative_distance_m=cumulative_distance,
        description=description,
        turn_type=turn_type,
        is_crosswalk=turn_type in _CROSSWALK_TURN_TYPES,
        is_stairs=turn_type in (127, 129),
    )


def _append_segment_points(
    route_points: list[RoutePoint],
    coordinates: tuple[Coordinate, ...],
    start_distance: float,
    segment_distance: float,
) -> None:
    _append_point_if_new(route_points, coordinates[0], start_distance)
    edge_lengths = [
        _haversine_meters(start, end) for start, end in zip(coordinates, coordinates[1:])
    ]
    measured_distance = sum(edge_lengths)
    distance_so_far = 0.0

    for index, (coordinate, edge_length) in enumerate(
        zip(coordinates[1:], edge_lengths),
        start=1,
    ):
        distance_so_far += edge_length
        if index == len(coordinates) - 1:
            point_distance = start_distance + segment_distance
        elif measured_distance > 0:
            point_distance = start_distance + segment_distance * distance_so_far / measured_distance
        else:
            point_distance = start_distance
        _append_point_if_new(route_points, coordinate, point_distance)


def _append_point_if_new(
    route_points: list[RoutePoint],
    coordinate: Coordinate,
    cumulative_distance: float,
) -> None:
    if route_points and _same_coordinate(route_points[-1], coordinate):
        return
    route_points.append(
        RoutePoint(
            longitude=coordinate.longitude,
            latitude=coordinate.latitude,
            cumulative_distance_m=cumulative_distance,
        )
    )


def _same_coordinate(point: RoutePoint, coordinate: Coordinate) -> bool:
    return point.longitude == coordinate.longitude and point.latitude == coordinate.latitude


def _haversine_meters(start: Coordinate, end: Coordinate) -> float:
    earth_radius_m = 6_371_000
    start_latitude = radians(start.latitude)
    end_latitude = radians(end.latitude)
    latitude_delta = end_latitude - start_latitude
    longitude_delta = radians(end.longitude - start.longitude)
    value = (
        sin(latitude_delta / 2) ** 2
        + cos(start_latitude) * cos(end_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(value))


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    result = float(value)
    return result if result > 0 else None


def _non_negative_float(value: object) -> float:
    result = float(value)
    if result < 0:
        raise ValueError("distance must be non-negative")
    return result


def _non_negative_int(value: object) -> int:
    result = int(value)
    if result < 0:
        raise ValueError("time must be non-negative")
    return result
