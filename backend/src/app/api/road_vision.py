from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import require_child
from app.core.errors import AppError
from app.schemas.common import RolePrincipal
from app.schemas.vision.road import RoadVisionResponse
from app.services.road_vision import (
    RoadVisionBusyError,
    RoadVisionMissionNotFoundError,
    RoadVisionService,
)

MAX_JPEG_BYTES = 1_000_000

router = APIRouter(tags=["road-vision"])


def get_road_vision_service() -> RoadVisionService:
    """Feature assembly supplies the concrete repository and OpenAI adapter."""
    raise AppError(
        code="ROAD_VISION_DEPENDENCY_NOT_CONFIGURED",
        message="도로 안전 판단 의존성이 구성되지 않았습니다.",
        status_code=503,
    )


Service = Annotated[RoadVisionService, Depends(get_road_vision_service)]
Child = Annotated[RolePrincipal, Depends(require_child)]


@router.post("/missions/{mission_id}/vision/road", response_model=RoadVisionResponse)
async def assess_road_safety(
    mission_id: str,
    captured_at: Annotated[datetime, Form(alias="capturedAt")],
    image: Annotated[UploadFile, File()],
    child: Child,
    service: Service,
) -> RoadVisionResponse:
    if child.mission_id != mission_id:
        raise AppError(
            code="AUTH_FORBIDDEN", message="이 작업을 수행할 권한이 없습니다.", status_code=403
        )
    if captured_at.tzinfo is None:
        raise AppError(
            code="VALIDATION_ERROR",
            message="capturedAt은 시간대를 포함해야 합니다.",
            status_code=422,
        )

    image_bytes = await image.read(MAX_JPEG_BYTES + 1)
    _validate_jpeg(image.content_type, image_bytes)
    try:
        evaluation = await service.evaluate(mission_id, image_bytes, captured_at)
    except RoadVisionBusyError:
        raise AppError(
            code="ROAD_VISION_BUSY", message="도로 상황 판단이 진행 중입니다.", status_code=409
        ) from None
    except RoadVisionMissionNotFoundError:
        raise AppError(
            code="MISSION_NOT_FOUND", message="미션을 찾을 수 없습니다.", status_code=404
        ) from None
    return RoadVisionResponse(result=evaluation.result, message=evaluation.message)


def _validate_jpeg(content_type: str | None, image: bytes) -> None:
    if (
        content_type not in {"image/jpeg", "image/jpg"}
        or not image.startswith(b"\xff\xd8")
        or not image.endswith(b"\xff\xd9")
    ):
        raise AppError(
            code="VALIDATION_ERROR", message="JPEG 이미지 한 장이 필요합니다.", status_code=422
        )
    if len(image) > MAX_JPEG_BYTES:
        raise AppError(
            code="VALIDATION_ERROR", message="이미지는 1MB 이하여야 합니다.", status_code=422
        )
