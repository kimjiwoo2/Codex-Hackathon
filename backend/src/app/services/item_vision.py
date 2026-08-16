from datetime import UTC, datetime
from typing import Protocol

from app.integrations.openai import VisionUnavailable
from app.models import ItemVerdict, MissionEventType, MissionStatus
from app.repositories import ItemVerification, MissionAggregate
from app.schemas.common import RolePrincipal
from app.schemas.vision.common import ProductVisionResult
from app.schemas.vision.item import ItemVerificationResponse

MAX_ITEM_IMAGE_BYTES = 1_000_000

_MESSAGES: dict[ItemVerdict, str] = {
    ItemVerdict.MATCH: "요청한 상품이 맞아요. 장바구니에 담아 주세요.",
    ItemVerdict.SIMILAR: "비슷한 상품이에요. 이름과 용량을 다시 확인해 주세요.",
    ItemVerdict.MISMATCH: "요청한 상품과 달라요. 다른 상품을 찾아 주세요.",
    ItemVerdict.UNKNOWN: "상품을 확인하지 못했어요. 다시 비추거나 부모님께 물어봐요.",
}


class InvalidItemImageError(ValueError):
    """Reject images that are not a bounded standalone JPEG sample."""


class ItemNotFoundError(LookupError):
    """Avoid revealing whether an item belongs to another mission."""


class InvalidItemVerificationStateError(ValueError):
    """Allow product verification only after the child has arrived at the store."""


class ItemVisionRepository(Protocol):
    def get_aggregate(self, mission_id: str) -> MissionAggregate | None: ...

    def update_item_verification(
        self,
        mission_id: str,
        item_id: str,
        verification: ItemVerification,
    ) -> object | None: ...

    def append_event(
        self,
        mission_id: str,
        event_type: MissionEventType,
        payload: dict[str, str],
    ) -> object: ...


class ProductVisionClient(Protocol):
    async def analyze_product(
        self,
        image: bytes,
        *,
        name: str,
        brand: str | None = None,
        size: str | None = None,
    ) -> object: ...


class ReturnHomeService(Protocol):
    def return_home(self, mission_id: str) -> object: ...


class ItemVisionService:
    """Compare one uploaded JPEG and retain only a normalized result."""

    def __init__(
        self,
        repository: ItemVisionRepository,
        vision_client: ProductVisionClient,
        mission_service: ReturnHomeService,
    ) -> None:
        self._repository = repository
        self._vision_client = vision_client
        self._mission_service = mission_service

    async def verify(
        self,
        *,
        mission_id: str,
        item_id: str,
        image: bytes,
        principal: RolePrincipal,
        now: datetime | None = None,
    ) -> ItemVerificationResponse:
        if principal.mission_id != mission_id:
            raise PermissionError("child token does not belong to this mission")
        _validate_jpeg(image)

        aggregate = self._repository.get_aggregate(mission_id)
        if aggregate is None:
            raise ItemNotFoundError(item_id)
        if aggregate.mission.status is not MissionStatus.SHOPPING:
            raise InvalidItemVerificationStateError("item verification requires SHOPPING status")
        item = next((candidate for candidate in aggregate.items if candidate.id == item_id), None)
        if item is None:
            raise ItemNotFoundError(item_id)

        detected_label: str | None = None
        description: str | None = None
        try:
            analysis = await self._vision_client.analyze_product(
                image,
                name=item.name,
                brand=item.brand,
                size=item.size,
            )
            verdict = _normalize_verdict(getattr(analysis, "result", None))
            detected_label = _optional_text(getattr(analysis, "detected_label", None), limit=300)
            description = _optional_text(getattr(analysis, "description", None), limit=500)
        except VisionUnavailable:
            verdict = ItemVerdict.UNKNOWN

        verified_at = (now or datetime.now(UTC)).astimezone(UTC)
        self._repository.update_item_verification(
            mission_id,
            item_id,
            ItemVerification(
                verdict=verdict,
                detected_label=detected_label,
                description=description,
                verified_at=verified_at,
            ),
        )
        self._repository.append_event(
            mission_id,
            MissionEventType.ITEM_VERIFIED,
            {"itemId": item_id, "verdict": verdict.value},
        )

        if _all_items_match(aggregate, item_id=item_id, new_verdict=verdict):
            self._mission_service.return_home(mission_id)

        return ItemVerificationResponse(
            verdict=verdict,
            message=_MESSAGES[verdict],
            detected_label=detected_label,
        )


def _validate_jpeg(image: bytes) -> None:
    if (
        not image
        or len(image) > MAX_ITEM_IMAGE_BYTES
        or not image.startswith(b"\xff\xd8\xff")
        or not image.endswith(b"\xff\xd9")
    ):
        raise InvalidItemImageError("image must be a JPEG no larger than 1MB")


def _normalize_verdict(value: object) -> ItemVerdict:
    if isinstance(value, (ItemVerdict, ProductVisionResult)):
        return ItemVerdict(value.value)
    if isinstance(value, str):
        try:
            return ItemVerdict(value.upper())
        except ValueError:
            pass
    return ItemVerdict.UNKNOWN


def _optional_text(value: object, *, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized[:limit] or None


def _all_items_match(
    aggregate: MissionAggregate,
    *,
    item_id: str,
    new_verdict: ItemVerdict,
) -> bool:
    return all(
        (new_verdict if item.id == item_id else item.last_verdict) is ItemVerdict.MATCH
        for item in aggregate.items
    )
