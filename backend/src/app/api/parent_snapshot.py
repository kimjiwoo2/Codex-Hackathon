from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import require_parent
from app.core.errors import AppError
from app.schemas.common import RolePrincipal
from app.schemas.parent import ParentSnapshotResponse
from app.services.parent_snapshot import ParentSnapshotNotFoundError, ParentSnapshotService

router = APIRouter(prefix="/missions", tags=["parent-snapshot"])


def get_parent_snapshot_service() -> ParentSnapshotService:
    """Feature assembly supplies the repository-backed polling service."""
    raise AppError(
        code="PARENT_SNAPSHOT_DEPENDENCY_NOT_CONFIGURED",
        message="부모 조회 의존성이 구성되지 않았습니다.",
        status_code=503,
    )


Service = Annotated[ParentSnapshotService, Depends(get_parent_snapshot_service)]
Parent = Annotated[RolePrincipal, Depends(require_parent)]


@router.get("/{mission_id}/snapshot", response_model=ParentSnapshotResponse)
def get_parent_snapshot(
    mission_id: str,
    service: Service,
    parent: Parent,
    after_event_id: Annotated[int, Query(alias="afterEventId", ge=0)] = 0,
) -> ParentSnapshotResponse:
    if parent.mission_id != mission_id:
        raise AppError(
            code="AUTH_FORBIDDEN", message="이 미션을 조회할 권한이 없습니다.", status_code=403
        )
    try:
        return service.get_snapshot(mission_id, after_event_id=after_event_id)
    except ParentSnapshotNotFoundError:
        raise AppError(
            code="MISSION_NOT_FOUND", message="미션을 찾을 수 없습니다.", status_code=404
        ) from None
