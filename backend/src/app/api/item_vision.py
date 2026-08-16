from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import require_child
from app.core.errors import AppError
from app.schemas.common import RolePrincipal
from app.schemas.vision.item import ItemVerificationResponse
from app.services.item_vision import (
    MAX_ITEM_IMAGE_BYTES,
    InvalidItemImageError,
    InvalidItemVerificationStateError,
    ItemNotFoundError,
    ItemVisionService,
)

router = APIRouter(tags=["item-vision"])


def get_item_vision_service() -> ItemVisionService:
    """Feature assembly supplies concrete persistence and OpenAI dependencies."""
    raise AppError(
        code="ITEM_VISION_DEPENDENCY_NOT_CONFIGURED",
        message="상품 확인 기능이 아직 구성되지 않았습니다.",
        status_code=503,
    )


ItemVisionServiceDependency = Annotated[ItemVisionService, Depends(get_item_vision_service)]
ChildPrincipal = Annotated[RolePrincipal, Depends(require_child)]


@router.post(
    "/missions/{mission_id}/items/{item_id}/verify",
    response_model=ItemVerificationResponse,
)
async def verify_item(
    mission_id: str,
    item_id: str,
    image: Annotated[UploadFile, File(...)],
    principal: ChildPrincipal,
    service: ItemVisionServiceDependency,
) -> ItemVerificationResponse:
    """Verify one bounded JPEG while discarding the upload after the OpenAI call."""
    try:
        if image.content_type not in (None, "image/jpeg"):
            raise InvalidItemImageError("image content type must be image/jpeg")
        contents = await image.read(MAX_ITEM_IMAGE_BYTES + 1)
        return await service.verify(
            mission_id=mission_id,
            item_id=item_id,
            image=contents,
            principal=principal,
        )
    except PermissionError:
        raise AppError(
            code="AUTH_FORBIDDEN",
            message="이 미션의 상품을 확인할 권한이 없습니다.",
            status_code=403,
        ) from None
    except ItemNotFoundError:
        raise AppError(
            code="ITEM_NOT_FOUND",
            message="요청한 상품을 찾을 수 없습니다.",
            status_code=404,
        ) from None
    except InvalidItemVerificationStateError:
        raise AppError(
            code="INVALID_STATUS_TRANSITION",
            message="상품 확인은 마트에 도착한 뒤에 할 수 있습니다.",
            status_code=409,
        ) from None
    except InvalidItemImageError:
        raise AppError(
            code="INVALID_ITEM_IMAGE",
            message="1MB 이하 JPEG 이미지가 필요합니다.",
            status_code=422,
        ) from None
    finally:
        await image.close()
