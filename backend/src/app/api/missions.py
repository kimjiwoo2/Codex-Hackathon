from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import require_parent
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.schemas.common import RolePrincipal
from app.schemas.mission import (
    CreateMissionRequest,
    CreateMissionResponse,
    JoinMissionRequest,
    JoinMissionResponse,
    ReturnHomeResponse,
)
from app.services.mission import MissionService

router = APIRouter(prefix="/missions", tags=["missions"])


def get_mission_service(settings: Annotated[Settings, Depends(get_settings)]) -> MissionService:
    raise AppError(
        code="MISSION_DEPENDENCY_NOT_CONFIGURED",
        message="미션 서비스 의존성이 구성되지 않았습니다.",
        status_code=503,
    )


Service = Annotated[MissionService, Depends(get_mission_service)]
Parent = Annotated[RolePrincipal, Depends(require_parent)]


@router.post("", response_model=CreateMissionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(request: CreateMissionRequest, service: Service) -> CreateMissionResponse:
    return await service.create(request)


@router.post("/join", response_model=JoinMissionResponse)
def join_mission(request: JoinMissionRequest, service: Service) -> JoinMissionResponse:
    return service.join(request)


@router.post("/{mission_id}/commands/return-home", response_model=ReturnHomeResponse)
def return_home(mission_id: str, service: Service, principal: Parent) -> ReturnHomeResponse:
    if principal.mission_id != mission_id:
        raise AppError(
            code="AUTH_FORBIDDEN", message="이 미션에 대한 권한이 없습니다.", status_code=403
        )
    return service.return_home(mission_id)
