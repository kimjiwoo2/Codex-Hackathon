from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import require_child
from app.core.errors import AppError
from app.schemas.common import RolePrincipal
from app.schemas.navigation.guidance import LocationRequest, LocationResponse
from app.services.navigation import LocationService

router = APIRouter(prefix="/missions", tags=["locations"])


def get_location_service() -> LocationService:
    """Feature assembly supplies the repository-backed service at application wiring time."""
    raise AppError(
        code="LOCATION_DEPENDENCY_NOT_CONFIGURED",
        message="위치 안내 의존성이 구성되지 않았습니다.",
        status_code=503,
    )


LocationServiceDependency = Annotated[LocationService, Depends(get_location_service)]
ChildPrincipal = Annotated[RolePrincipal, Depends(require_child)]


@router.post("/{mission_id}/locations", response_model=LocationResponse)
def update_location(
    mission_id: str,
    request: LocationRequest,
    child: ChildPrincipal,
    service: LocationServiceDependency,
) -> LocationResponse:
    if child.mission_id != mission_id:
        raise AppError(
            code="AUTH_FORBIDDEN",
            message="다른 미션의 위치를 갱신할 수 없습니다.",
            status_code=403,
        )
    try:
        return service.update(mission_id, request)
    except LookupError as error:
        raise AppError(
            code="MISSION_NOT_FOUND",
            message="미션을 찾을 수 없습니다.",
            status_code=404,
        ) from error
