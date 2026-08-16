from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.integrations.openai import VisionUnavailable
from app.models import ItemVerdict, MissionStatus
from app.repositories import MissionAggregate
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.vision.common import ProductVisionAnalysis, ProductVisionResult
from app.services.item_vision import InvalidItemImageError, ItemVisionService


def _aggregate(*verdicts: ItemVerdict) -> MissionAggregate:
    mission = SimpleNamespace(id="mission-1", status=MissionStatus.SHOPPING)
    items = tuple(
        SimpleNamespace(
            id=f"item-{index}",
            name="우유",
            brand="서울우유",
            size="1L",
            last_verdict=verdict,
        )
        for index, verdict in enumerate(verdicts, start=1)
    )
    return MissionAggregate(mission=mission, items=items)


def _service(
    *, analysis: object, aggregate: MissionAggregate | None = None
) -> tuple[ItemVisionService, Mock, AsyncMock, Mock]:
    repository = Mock()
    repository.get_aggregate.return_value = aggregate or _aggregate(ItemVerdict.UNKNOWN)
    repository.update_item_verification.side_effect = lambda _mission_id, item_id, verification: (
        SimpleNamespace(
            id=item_id,
            last_verdict=verification.verdict,
            detected_label=verification.detected_label,
            description=verification.description,
        )
    )
    vision_client = AsyncMock()
    vision_client.analyze_product.return_value = analysis
    mission_service = Mock()
    return (
        ItemVisionService(repository, vision_client, mission_service),
        repository,
        vision_client,
        mission_service,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("raw_result", "expected", "message"),
    [
        (
            ProductVisionResult.MATCH,
            ItemVerdict.MATCH,
            "요청한 상품이 맞아요. 장바구니에 담아 주세요.",
        ),
        (
            ProductVisionResult.SIMILAR,
            ItemVerdict.SIMILAR,
            "비슷한 상품이에요. 이름과 용량을 다시 확인해 주세요.",
        ),
        (
            ProductVisionResult.MISMATCH,
            ItemVerdict.MISMATCH,
            "요청한 상품과 달라요. 다른 상품을 찾아 주세요.",
        ),
        (
            ProductVisionResult.UNKNOWN,
            ItemVerdict.UNKNOWN,
            "상품을 확인하지 못했어요. 다시 비추거나 부모님께 물어봐요.",
        ),
    ],
)
async def test_verifies_product_with_fixed_message_and_persists_safe_fields(
    raw_result: ProductVisionResult,
    expected: ItemVerdict,
    message: str,
) -> None:
    analysis = ProductVisionAnalysis(
        result=raw_result,
        detectedLabel="서울우유 1L",
        description="This free-form model explanation must not become a child message.",
    )
    service, repository, vision_client, _ = _service(analysis=analysis)

    response = await service.verify(
        mission_id="mission-1",
        item_id="item-1",
        image=b"\xff\xd8\xffsample\xff\xd9",
        principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
        now=datetime(2026, 8, 16, tzinfo=UTC),
    )

    assert response.verdict is expected
    assert response.message == message
    assert response.detected_label == "서울우유 1L"
    vision_client.analyze_product.assert_awaited_once_with(
        b"\xff\xd8\xffsample\xff\xd9", name="우유", brand="서울우유", size="1L"
    )
    persisted = repository.update_item_verification.call_args.args[2]
    assert persisted.verdict is expected
    assert persisted.description == analysis.description
    assert b"\xff\xd8\xffsample\xff\xd9" not in repository.mock_calls


@pytest.mark.anyio
async def test_unknown_model_result_is_clamped_and_vision_failure_is_unknown() -> None:
    service, repository, _, _ = _service(
        analysis=SimpleNamespace(result="CROSS_OK", detected_label="우유", description="free form")
    )

    response = await service.verify(
        mission_id="mission-1",
        item_id="item-1",
        image=b"\xff\xd8\xffsample\xff\xd9",
        principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
    )

    assert response.verdict is ItemVerdict.UNKNOWN
    assert response.message == "상품을 확인하지 못했어요. 다시 비추거나 부모님께 물어봐요."
    assert repository.update_item_verification.call_args.args[2].description == "free form"


@pytest.mark.anyio
async def test_vision_failure_is_stored_as_unknown_without_adapter_text() -> None:
    service, repository, vision_client, _ = _service(
        analysis=ProductVisionAnalysis(result="MATCH", description="match")
    )
    vision_client.analyze_product.side_effect = VisionUnavailable()

    response = await service.verify(
        mission_id="mission-1",
        item_id="item-1",
        image=b"\xff\xd8\xffsample\xff\xd9",
        principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
    )

    assert response.verdict is ItemVerdict.UNKNOWN
    assert response.detected_label is None
    persisted = repository.update_item_verification.call_args.args[2]
    assert persisted.description is None


@pytest.mark.anyio
async def test_all_matching_items_request_safe_return_home_transition() -> None:
    service, _, _, mission_service = _service(
        analysis=ProductVisionAnalysis(result="MATCH", description="match"),
        aggregate=_aggregate(ItemVerdict.MATCH, ItemVerdict.UNKNOWN),
    )

    await service.verify(
        mission_id="mission-1",
        item_id="item-2",
        image=b"\xff\xd8\xffsample\xff\xd9",
        principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
    )

    mission_service.return_home.assert_called_once_with("mission-1")


@pytest.mark.anyio
async def test_rejects_item_from_another_mission_without_calling_vision() -> None:
    service, repository, vision_client, _ = _service(
        analysis=ProductVisionAnalysis(result="MATCH", description="match")
    )

    with pytest.raises(PermissionError):
        await service.verify(
            mission_id="other-mission",
            item_id="item-1",
            image=b"\xff\xd8\xffsample\xff\xd9",
            principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
        )

    repository.get_aggregate.assert_not_called()
    vision_client.analyze_product.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "image",
    [b"not-a-jpeg", b"\xff\xd8\xff" + b"x" * (1_000_001) + b"\xff\xd9"],
)
async def test_rejects_non_jpeg_and_oversized_image_without_persisting_or_analyzing(
    image: bytes,
) -> None:
    service, repository, vision_client, _ = _service(
        analysis=ProductVisionAnalysis(result="MATCH", description="match")
    )

    with pytest.raises(InvalidItemImageError):
        await service.verify(
            mission_id="mission-1",
            item_id="item-1",
            image=image,
            principal=RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD),
        )

    repository.get_aggregate.assert_not_called()
    repository.update_item_verification.assert_not_called()
    vision_client.analyze_product.assert_not_awaited()
