import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app.core.config import Settings
from app.db.base import Base
from app.integrations.openai import VisionUnavailable
from app.main import ApplicationComponents, assemble_components
from app.repositories.missions import MissionSeed
from app.schemas.navigation.route import (
    Coordinate,
    RoundTripRoutes,
    Route,
    RoutePoint,
    RouteStep,
    RouteStepKind,
)
from app.schemas.vision.common import (
    ProductVisionAnalysis,
    ProductVisionResult,
    RoadVisionAnalysis,
    RoadVisionResult,
)
from app.security.tokens import generate_opaque_token, hash_opaque_token

JPG = b"\xff\xd8\xffdemo\xff\xd9"
HOME = Coordinate(latitude=37.0, longitude=127.0)
STORE = Coordinate(latitude=37.0002, longitude=127.0)


@dataclass
class TmapDouble:
    routes: RoundTripRoutes
    calls: int = 0

    async def get_round_trip(self, home: Coordinate, destination: Coordinate) -> RoundTripRoutes:
        assert home == HOME
        assert destination == STORE
        self.calls += 1
        return self.routes


@dataclass
class VisionDouble:
    road_result: RoadVisionResult = RoadVisionResult.CAUTION
    product_result: ProductVisionResult = ProductVisionResult.MATCH

    async def analyze_road(self, image: bytes) -> RoadVisionAnalysis:
        assert image == JPG
        return RoadVisionAnalysis(result=self.road_result, description="normalized")

    async def analyze_product(
        self,
        image: bytes,
        *,
        name: str,
        brand: str | None = None,
        size: str | None = None,
    ) -> ProductVisionAnalysis:
        assert image == JPG
        assert (name, brand, size) == ("우유", "서울우유", "1L")
        return ProductVisionAnalysis(
            result=self.product_result,
            detectedLabel="서울우유 1L",
            description="normalized",
        )


class VisionUnavailableDouble(VisionDouble):
    async def analyze_road(self, image: bytes) -> RoadVisionAnalysis:
        raise VisionUnavailable


class ForbiddenRoadVisionDouble(VisionDouble):
    async def analyze_road(self, image: bytes) -> SimpleNamespace:
        assert image == JPG
        return SimpleNamespace(result="CROSS_OK", description="건너도 된다")


def _routes() -> RoundTripRoutes:
    midpoint = Coordinate(latitude=37.0001, longitude=127.0)
    outbound = Route(
        total_distance_m=22.0,
        total_time_seconds=30,
        points=(
            RoutePoint(**HOME.model_dump(), cumulative_distance_m=0),
            RoutePoint(**midpoint.model_dump(), cumulative_distance_m=11),
            RoutePoint(**STORE.model_dump(), cumulative_distance_m=22),
        ),
        steps=(
            RouteStep(
                index=0,
                kind=RouteStepKind.START,
                coordinate=HOME,
                cumulative_distance_m=0,
            ),
            RouteStep(
                index=1,
                kind=RouteStepKind.CROSSWALK,
                coordinate=midpoint,
                cumulative_distance_m=11,
                is_crosswalk=True,
            ),
            RouteStep(
                index=2,
                kind=RouteStepKind.ARRIVE,
                coordinate=STORE,
                cumulative_distance_m=22,
            ),
        ),
    )
    returning = Route(
        total_distance_m=22.0,
        total_time_seconds=30,
        points=(
            RoutePoint(**STORE.model_dump(), cumulative_distance_m=0),
            RoutePoint(**midpoint.model_dump(), cumulative_distance_m=11),
            RoutePoint(**HOME.model_dump(), cumulative_distance_m=22),
        ),
        steps=(
            RouteStep(
                index=0,
                kind=RouteStepKind.START,
                coordinate=STORE,
                cumulative_distance_m=0,
            ),
            RouteStep(
                index=1,
                kind=RouteStepKind.STRAIGHT,
                coordinate=midpoint,
                cumulative_distance_m=11,
            ),
            RouteStep(
                index=2,
                kind=RouteStepKind.ARRIVE,
                coordinate=HOME,
                cumulative_distance_m=22,
            ),
        ),
    )
    return RoundTripRoutes(outbound=outbound, returning=returning)


def _components(vision: VisionDouble) -> tuple[ApplicationComponents, TmapDouble]:
    engine: Engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    tmap = TmapDouble(_routes())
    return assemble_components(
        settings=Settings(app_env="test"),
        engine=engine,
        tmap_client=tmap,
        vision_client=vision,
    ), tmap


def _seed_joinable_mission(
    components: ApplicationComponents,
    *,
    join_code: str,
    parent_token: str,
) -> str:
    routes = _routes()
    aggregate = components.repository.create_mission(
        MissionSeed(
            home_lat=HOME.latitude,
            home_lng=HOME.longitude,
            store_lat=STORE.latitude,
            store_lng=STORE.longitude,
            outbound_route=routes.outbound.model_dump(mode="json"),
            return_route=routes.returning.model_dump(mode="json"),
            parent_token_hash=hash_opaque_token(parent_token),
            join_code=join_code,
            join_code_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        ),
        [],
    )
    return aggregate.mission.id


def _location(coordinate: Coordinate) -> dict[str, object]:
    return {
        "latitude": coordinate.latitude,
        "longitude": coordinate.longitude,
        "accuracy_m": 5,
        "heading_deg": 0,
        "observed_at": datetime.now(UTC).isoformat(),
    }


@pytest.mark.anyio
async def test_real_create_app_completes_demo_e2e_with_shared_sqlite_graph(
    composed_app_factory: Callable[[ApplicationComponents], FastAPI],
) -> None:
    components, tmap = _components(VisionDouble())
    app = composed_app_factory(components)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        created = await client.post(
            "/missions",
            json={
                "home": HOME.model_dump(),
                "store": STORE.model_dump(),
                "items": [{"name": "우유", "brand": "서울우유", "size": "1L"}],
            },
        )
        assert created.status_code == 201
        mission = created.json()
        assert len(mission["joinCode"]) == 6

        joined = await client.post("/missions/join", json={"joinCode": mission["joinCode"]})
        assert joined.status_code == 200
        child_headers = {"Authorization": f"Bearer {joined.json()['childToken']}"}
        parent_headers = {"Authorization": f"Bearer {mission['parentToken']}"}

        guidance = await client.post(
            f"/missions/{mission['missionId']}/locations",
            json=_location(HOME),
            headers=child_headers,
        )
        assert guidance.status_code == 200
        assert guidance.json()["instruction_code"] == "CROSSWALK_STOP"

        for _ in range(2):
            at_store = await client.post(
                f"/missions/{mission['missionId']}/locations",
                json=_location(STORE),
                headers=child_headers,
            )
        assert at_store.json()["status"] == "SHOPPING"

        road = await client.post(
            f"/missions/{mission['missionId']}/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("road.jpg", JPG, "image/jpeg")},
            headers=child_headers,
        )
        assert road.status_code == 200
        assert road.json()["result"] == "CAUTION"

        aggregate = components.repository.get_aggregate(mission["missionId"])
        assert aggregate is not None
        item_id = aggregate.items[0].id
        item = await client.post(
            f"/missions/{mission['missionId']}/items/{item_id}/verify",
            files={"image": ("milk.jpg", JPG, "image/jpeg")},
            headers=child_headers,
        )
        assert item.status_code == 200
        assert item.json()["verdict"] == "MATCH"

        returning = await client.post(
            f"/missions/{mission['missionId']}/commands/return-home", headers=parent_headers
        )
        assert returning.status_code == 200
        assert returning.json()["status"] == "RETURNING"

        at_home = await client.post(
            f"/missions/{mission['missionId']}/locations",
            json=_location(HOME),
            headers=child_headers,
        )
        assert at_home.status_code == 200
        assert at_home.json()["status"] == "COMPLETED"

        snapshot = await client.get(
            f"/missions/{mission['missionId']}/snapshot", headers=parent_headers
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["status"] == "COMPLETED"
        assert snapshot.json()["items"][0]["verdict"] == "MATCH"
        cursor = snapshot.json()["nextEventId"]
        no_duplicate_events = await client.get(
            f"/missions/{mission['missionId']}/snapshot?afterEventId={cursor}",
            headers=parent_headers,
        )

    assert no_duplicate_events.status_code == 200
    assert no_duplicate_events.json()["events"] == []
    assert tmap.calls == 1


@pytest.mark.anyio
async def test_vision_unavailable_never_exposes_crossing_permission_in_api_event_or_tts(
    composed_app_factory: Callable[[ApplicationComponents], FastAPI],
) -> None:
    components, _ = _components(VisionUnavailableDouble())
    app = composed_app_factory(components)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        created = await client.post(
            "/missions",
            json={
                "home": HOME.model_dump(),
                "store": STORE.model_dump(),
                "items": [{"name": "우유"}],
            },
        )
        mission = created.json()
        joined = await client.post("/missions/join", json={"joinCode": mission["joinCode"]})
        child_headers = {"Authorization": f"Bearer {joined.json()['childToken']}"}
        parent_headers = {"Authorization": f"Bearer {mission['parentToken']}"}
        await client.post(
            f"/missions/{mission['missionId']}/locations",
            json=_location(STORE),
            headers=child_headers,
        )

        road = await client.post(
            f"/missions/{mission['missionId']}/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("road.jpg", JPG, "image/jpeg")},
            headers=child_headers,
        )
        snapshot = await client.get(
            f"/missions/{mission['missionId']}/snapshot", headers=parent_headers
        )

    assert road.status_code == 200
    assert road.json()["result"] == "UNKNOWN"
    assert "멈추고" in road.json()["message"]
    assert snapshot.status_code == 200
    assert snapshot.json()["events"][0]["eventType"] == "VISION_UNAVAILABLE"
    serialized = json.dumps({"road": road.json(), "snapshot": snapshot.json()}, ensure_ascii=False)
    assert "CROSS_OK" not in serialized
    assert "건너도 된다" not in serialized


@pytest.mark.anyio
async def test_forbidden_vision_output_is_clamped_before_api_event_or_tts(
    composed_app_factory: Callable[[ApplicationComponents], FastAPI],
) -> None:
    components, _ = _components(ForbiddenRoadVisionDouble())
    app = composed_app_factory(components)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        created = await client.post(
            "/missions",
            json={
                "home": HOME.model_dump(),
                "store": STORE.model_dump(),
                "items": [{"name": "우유"}],
            },
        )
        mission = created.json()
        joined = await client.post("/missions/join", json={"joinCode": mission["joinCode"]})
        child_headers = {"Authorization": f"Bearer {joined.json()['childToken']}"}
        parent_headers = {"Authorization": f"Bearer {mission['parentToken']}"}

        road = await client.post(
            f"/missions/{mission['missionId']}/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("road.jpg", JPG, "image/jpeg")},
            headers=child_headers,
        )
        snapshot = await client.get(
            f"/missions/{mission['missionId']}/snapshot", headers=parent_headers
        )

    assert road.status_code == 200
    assert road.json()["result"] in {"STOP", "CAUTION", "UNKNOWN"}
    assert snapshot.status_code == 200
    serialized = json.dumps({"road": road.json(), "snapshot": snapshot.json()}, ensure_ascii=False)
    assert "CROSS_OK" not in serialized
    assert "건너도 된다" not in serialized


@pytest.mark.anyio
async def test_production_assembly_degrades_missing_external_keys_per_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine: Engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main_module, "create_neon_engine", lambda _database_url: engine)
    app = main_module.create_app(
        settings=Settings(database_url="postgresql+psycopg://runtime@example-pooler.neon.tech/db")
    )

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        create = await client.post(
            "/missions",
            json={
                "home": HOME.model_dump(),
                "store": STORE.model_dump(),
                "items": [{"name": "우유"}],
            },
        )
        assert create.status_code == 503
        assert create.json()["error"]["code"] == "TMAP_UNAVAILABLE"

        components = app.state.components
        assert isinstance(components, ApplicationComponents)
        parent_token = generate_opaque_token()
        mission_id = _seed_joinable_mission(
            components,
            join_code="123456",
            parent_token=parent_token,
        )
        joined = await client.post("/missions/join", json={"joinCode": "123456"})
        assert joined.status_code == 200
        child_headers = {"Authorization": f"Bearer {joined.json()['childToken']}"}
        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        location = await client.post(
            f"/missions/{mission_id}/locations", json=_location(STORE), headers=child_headers
        )
        road = await client.post(
            f"/missions/{mission_id}/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("road.jpg", JPG, "image/jpeg")},
            headers=child_headers,
        )
        snapshot = await client.get(f"/missions/{mission_id}/snapshot", headers=parent_headers)

    assert location.status_code == 200
    assert road.status_code == 200
    assert road.json()["result"] == "UNKNOWN"
    assert snapshot.status_code == 200
