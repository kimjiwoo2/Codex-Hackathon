from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import missions
from app.api.dependencies import get_role_token_verifier
from app.api.errors import register_error_handlers
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.mission import CreateMissionResponse, JoinMissionResponse, ReturnHomeResponse


class _Service:
    async def create(self, _request):
        return CreateMissionResponse(
            mission_id="mission-1", join_code="123456", parent_token="a" * 43
        )

    def join(self, _request):
        return JoinMissionResponse(
            mission_id="mission-1",
            child_token="b" * 43,
            status="GOING",
            instruction_code="START_OUTBOUND",
            message="마트로 출발해요.",
        )

    def return_home(self, _mission_id):
        return ReturnHomeResponse(
            status="RETURNING",
            return_strategy="RETRACE_OUTBOUND_FROM_PROGRESS",
            outbound_progress_m=12.0,
        )


class _Verifier:
    def verify(self, token, expected_role):
        if token == "parent" and expected_role is MissionRole.PARENT:
            return RolePrincipal(mission_id="mission-1", role=MissionRole.PARENT)
        if token == "child" and expected_role is MissionRole.CHILD:
            return RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD)
        return None


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(missions.router)
    app.dependency_overrides[missions.get_mission_service] = lambda: _Service()
    app.dependency_overrides[get_role_token_verifier] = lambda: _Verifier()
    return TestClient(app)


def test_create_and_join_are_public_but_return_requires_parent() -> None:
    client = _client()

    created = client.post(
        "/missions",
        json={
            "home": {"longitude": 126.97, "latitude": 37.56},
            "store": {"longitude": 126.98, "latitude": 37.57},
            "items": [{"name": "우유"}],
        },
    )
    joined = client.post("/missions/join", json={"joinCode": "123456"})
    forbidden = client.post(
        "/missions/mission-1/commands/return-home", headers={"Authorization": "Bearer child"}
    )
    returned = client.post(
        "/missions/mission-1/commands/return-home", headers={"Authorization": "Bearer parent"}
    )

    assert created.status_code == 201
    assert joined.status_code == 200
    assert forbidden.status_code == 403
    assert returned.status_code == 200
    assert returned.json()["returnStrategy"] == "RETRACE_OUTBOUND_FROM_PROGRESS"
