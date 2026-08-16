from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import require_child
from app.api.errors import register_error_handlers
from app.api.road_vision import get_road_vision_service, router
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.vision.common import RoadVisionResult
from app.services.road_vision import RoadVisionService


@pytest.fixture
def road_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[require_child] = lambda: RolePrincipal(
        mission_id="mission-1", role=MissionRole.CHILD
    )
    return app


@pytest.mark.anyio
async def test_road_api_rejects_non_jpeg_and_never_calls_service(road_app: FastAPI) -> None:
    service = AsyncMock(spec=RoadVisionService)
    road_app.dependency_overrides[get_road_vision_service] = lambda: service
    transport = ASGITransport(app=road_app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/missions/mission-1/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("frame.png", b"not-jpeg", "image/png")},
        )

    assert response.status_code == 422
    service.evaluate.assert_not_awaited()


@pytest.mark.anyio
async def test_road_api_rejects_jpeg_larger_than_one_megabyte(road_app: FastAPI) -> None:
    service = AsyncMock(spec=RoadVisionService)
    road_app.dependency_overrides[get_road_vision_service] = lambda: service
    oversized_jpeg = b"\xff\xd8" + b"x" * 1_000_000 + b"\xff\xd9"
    transport = ASGITransport(app=road_app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/missions/mission-1/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("frame.jpg", oversized_jpeg, "image/jpeg")},
        )

    assert response.status_code == 422
    service.evaluate.assert_not_awaited()


@pytest.mark.anyio
async def test_road_api_returns_only_fixed_safe_message(road_app: FastAPI) -> None:
    service = AsyncMock(spec=RoadVisionService)
    service.evaluate.return_value = SimpleNamespace(
        result=RoadVisionResult.CAUTION,
        message="주변을 살피고 보호자와 함께 확인하세요.",
    )
    road_app.dependency_overrides[get_road_vision_service] = lambda: service
    transport = ASGITransport(app=road_app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/missions/mission-1/vision/road",
            data={"capturedAt": datetime.now(UTC).isoformat()},
            files={"image": ("frame.jpg", b"\xff\xd8jpeg\xff\xd9", "image/jpeg")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "result": "CAUTION",
        "message": "주변을 살피고 보호자와 함께 확인하세요.",
    }
