from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import parent_snapshot
from app.api.dependencies import get_role_token_verifier
from app.api.errors import register_error_handlers
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.parent import ParentSnapshotResponse


class _Service:
    def __init__(self) -> None:
        self.after_event_id: int | None = None

    def get_snapshot(self, mission_id: str, *, after_event_id: int) -> ParentSnapshotResponse:
        self.after_event_id = after_event_id
        return ParentSnapshotResponse(
            mission_id=mission_id,
            status="GOING",
            location=None,
            location_stale=True,
            remaining_distance_m=0,
            items=(),
            events=(),
            next_event_id=after_event_id,
        )


class _Verifier:
    def verify(self, token, expected_role):
        if token == "parent" and expected_role is MissionRole.PARENT:
            return RolePrincipal(mission_id="mission-1", role=MissionRole.PARENT)
        if token == "other-parent" and expected_role is MissionRole.PARENT:
            return RolePrincipal(mission_id="mission-2", role=MissionRole.PARENT)
        if token == "child" and expected_role is MissionRole.CHILD:
            return RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD)
        return None


def _client() -> tuple[TestClient, _Service]:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(parent_snapshot.router)
    service = _Service()
    app.dependency_overrides[parent_snapshot.get_parent_snapshot_service] = lambda: service
    app.dependency_overrides[get_role_token_verifier] = lambda: _Verifier()
    return TestClient(app), service


def test_snapshot_requires_its_parent_token_and_passes_cursor() -> None:
    client, service = _client()

    missing = client.get("/missions/mission-1/snapshot")
    child = client.get("/missions/mission-1/snapshot", headers={"Authorization": "Bearer child"})
    other = client.get(
        "/missions/mission-1/snapshot", headers={"Authorization": "Bearer other-parent"}
    )
    allowed = client.get(
        "/missions/mission-1/snapshot?afterEventId=8",
        headers={"Authorization": "Bearer parent"},
    )

    assert missing.status_code == 401
    assert child.status_code == 403
    assert other.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["nextEventId"] == 8
    assert service.after_event_id == 8
