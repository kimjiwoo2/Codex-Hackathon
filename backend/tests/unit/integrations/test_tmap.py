import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.integrations.tmap import TmapClient, TmapUnavailable, normalize_route
from app.schemas.navigation.route import Coordinate, RouteStepKind

FIXTURE_PATH = Path(__file__).parents[2] / "fixtures" / "tmap" / "pedestrian_route.json"


@pytest.fixture
def pedestrian_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text())


def test_normalizes_official_geojson_into_route_contract(
    pedestrian_payload: dict[str, Any],
) -> None:
    route = normalize_route(pedestrian_payload)

    assert route.total_distance_m == 50
    assert route.total_time_seconds == 60
    assert [point.cumulative_distance_m for point in route.points] == [0, 10, 30, 40, 50]
    assert route.geometry == route.points
    assert "points" in route.model_dump()
    assert "geometry" not in route.model_dump()
    assert [step.kind for step in route.steps] == [
        RouteStepKind.START,
        RouteStepKind.STAIRS,
        RouteStepKind.LEFT_TURN,
        RouteStepKind.RIGHT_TURN,
        RouteStepKind.CROSSWALK,
        RouteStepKind.CROSSWALK,
        RouteStepKind.ARRIVE,
    ]

    stairs = route.steps[1]
    assert stairs.facility_type == 17
    assert stairs.is_stairs is True
    assert stairs.cumulative_distance_m == 0

    left, right = route.steps[2:4]
    assert (left.turn_type, left.cumulative_distance_m) == (12, 10)
    assert (right.turn_type, right.cumulative_distance_m) == (13, 30)

    crosswalk_turn, crosswalk_segment = route.steps[4:6]
    assert crosswalk_turn.turn_type == 211
    assert crosswalk_turn.is_crosswalk is True
    assert crosswalk_segment.facility_type == 15
    assert crosswalk_segment.is_crosswalk is True


@pytest.mark.anyio
async def test_requests_pedestrian_route_with_bounded_timeout_and_app_key(
    pedestrian_payload: dict[str, Any],
) -> None:
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(200, json=pedestrian_payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TmapClient(
            app_key="test-app-key",
            http_client=http_client,
            timeout_seconds=3.5,
        )
        route = await client.get_pedestrian_route(
            Coordinate(longitude=126.9, latitude=37.5),
            Coordinate(longitude=127.0, latitude=37.6),
            start_name="집",
            end_name="마트",
        )

    assert route.total_distance_m == 50
    assert seen_request is not None
    assert seen_request.method == "POST"
    assert seen_request.url.path == "/tmap/routes/pedestrian"
    assert seen_request.url.params["version"] == "1"
    assert seen_request.headers["appKey"] == "test-app-key"
    assert seen_request.headers["Accept"] == "application/json"
    assert seen_request.headers["Content-Type"] == "application/json"
    assert json.loads(seen_request.content) == {
        "angle": 0,
        "speed": 0,
        "reqCoordType": "WGS84GEO",
        "searchOption": "0",
        "resCoordType": "WGS84GEO",
        "sort": "index",
        "startX": 126.9,
        "startY": 37.5,
        "endX": 127.0,
        "endY": 37.6,
        "startName": "%EC%A7%91",
        "endName": "%EB%A7%88%ED%8A%B8",
    }
    assert seen_request.extensions["timeout"] == {
        "connect": 3.5,
        "read": 3.5,
        "write": 3.5,
        "pool": 3.5,
    }


@pytest.mark.anyio
async def test_prepares_outbound_and_return_routes_in_order(
    pedestrian_payload: dict[str, Any],
) -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=pedestrian_payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TmapClient(app_key="test-app-key", http_client=http_client)
        routes = await client.get_round_trip(
            home=Coordinate(longitude=126.9, latitude=37.5),
            destination=Coordinate(longitude=127.0, latitude=37.6),
        )

    assert routes.outbound.total_distance_m == 50
    assert routes.returning.total_distance_m == 50
    assert [(body["startX"], body["endX"]) for body in bodies] == [
        (126.9, 127.0),
        (127.0, 126.9),
    ]
    assert [(body["startName"], body["endName"]) for body in bodies] == [
        ("%EC%A7%91", "%EB%A7%88%ED%8A%B8"),
        ("%EB%A7%88%ED%8A%B8", "%EC%A7%91"),
    ]


def _error_handler(error: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 401, 429, 500, 503])
async def test_normalizes_http_failures_as_tmap_unavailable(status_code: int) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(status_code, json={"error": "x"}))
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TmapClient(app_key="test-app-key", http_client=http_client)

        with pytest.raises(TmapUnavailable) as error:
            await client.get_pedestrian_route(
                Coordinate(longitude=126.9, latitude=37.5),
                Coordinate(longitude=127.0, latitude=37.6),
            )

    assert error.value.code == "TMAP_UNAVAILABLE"
    assert error.value.status_code == 503


@pytest.mark.anyio
async def test_normalizes_timeout_as_tmap_unavailable() -> None:
    transport = httpx.MockTransport(_error_handler(httpx.ReadTimeout("timed out")))
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = TmapClient(app_key="test-app-key", http_client=http_client)

        with pytest.raises(TmapUnavailable):
            await client.get_pedestrian_route(
                Coordinate(longitude=126.9, latitude=37.5),
                Coordinate(longitude=127.0, latitude=37.6),
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "FeatureCollection", "features": []},
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [126.9, 37.5]},
                    "properties": {"index": 0, "turnType": 200},
                }
            ],
        },
        {"unexpected": "shape"},
    ],
)
def test_rejects_empty_or_malformed_routes(payload: dict[str, Any]) -> None:
    with pytest.raises(TmapUnavailable):
        normalize_route(payload)
