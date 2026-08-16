from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import require_child
from app.api.errors import register_error_handlers
from app.api.item_vision import get_item_vision_service, router
from app.models import ItemVerdict, MissionStatus
from app.repositories import MissionAggregate
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.vision.common import ProductVisionAnalysis
from app.services.item_vision import ItemVisionService


@pytest.fixture
def item_api() -> tuple[FastAPI, Mock, AsyncMock]:
    repository = Mock()
    item = SimpleNamespace(
        id="item-1",
        name="우유",
        brand="서울우유",
        size="1L",
        last_verdict=ItemVerdict.UNKNOWN,
    )
    repository.get_aggregate.return_value = MissionAggregate(
        mission=SimpleNamespace(id="mission-1", status=MissionStatus.SHOPPING),
        items=(item,),
    )
    repository.update_item_verification.return_value = item
    vision_client = AsyncMock()
    vision_client.analyze_product.return_value = ProductVisionAnalysis(
        result="MATCH",
        detectedLabel="서울우유 1L",
        description="free-form adapter text",
    )
    mission_service = Mock()
    service = ItemVisionService(repository, vision_client, mission_service)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[require_child] = lambda: RolePrincipal(
        mission_id="mission-1", role=MissionRole.CHILD
    )
    app.dependency_overrides[get_item_vision_service] = lambda: service
    return app, repository, vision_client


@pytest.mark.anyio
async def test_verify_item_returns_fixed_contract_and_never_persists_upload(
    item_api: tuple[FastAPI, Mock, AsyncMock],
) -> None:
    app, repository, vision_client = item_api
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(
            "/missions/mission-1/items/item-1/verify",
            files={"image": ("milk.jpg", b"\xff\xd8\xffsample\xff\xd9", "image/jpeg")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "verdict": "MATCH",
        "message": "요청한 상품이 맞아요. 장바구니에 담아 주세요.",
        "detectedLabel": "서울우유 1L",
    }
    vision_client.analyze_product.assert_awaited_once()
    repository.append_event.assert_called_once_with(
        "mission-1",
        "ITEM_VERIFIED",
        {"itemId": "item-1", "verdict": "MATCH"},
    )
    assert b"\xff\xd8\xffsample\xff\xd9" not in repository.mock_calls


@pytest.mark.anyio
async def test_verify_item_rejects_non_jpeg_before_vision_call(
    item_api: tuple[FastAPI, Mock, AsyncMock],
) -> None:
    app, repository, vision_client = item_api
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(
            "/missions/mission-1/items/item-1/verify",
            files={"image": ("milk.png", b"not-an-image", "image/png")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ITEM_IMAGE"
    repository.update_item_verification.assert_not_called()
    vision_client.analyze_product.assert_not_awaited()


@pytest.mark.anyio
async def test_verify_item_rejects_non_shopping_mission_before_vision_or_persistence(
    item_api: tuple[FastAPI, Mock, AsyncMock],
) -> None:
    app, repository, vision_client = item_api
    repository.get_aggregate.return_value.mission.status = MissionStatus.GOING
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(
            "/missions/mission-1/items/item-1/verify",
            files={"image": ("milk.jpg", b"\xff\xd8\xffsample\xff\xd9", "image/jpeg")},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    vision_client.analyze_product.assert_not_awaited()
    repository.update_item_verification.assert_not_called()
    repository.append_event.assert_not_called()


@pytest.mark.anyio
async def test_verify_item_blocks_other_mission_path(
    item_api: tuple[FastAPI, Mock, AsyncMock],
) -> None:
    app, _, vision_client = item_api
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.post(
            "/missions/other-mission/items/item-1/verify",
            files={"image": ("milk.jpg", b"\xff\xd8\xffsample\xff\xd9", "image/jpeg")},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_FORBIDDEN"
    vision_client.analyze_product.assert_not_awaited()
