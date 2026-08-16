from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import locations
from app.api.dependencies import get_role_token_verifier
from app.api.errors import register_error_handlers
from app.schemas.common import MissionRole, RolePrincipal
from app.schemas.navigation.guidance import (
    InstructionCode,
    LocationResponse,
    VibrationHint,
)


class _LocationService:
    def update(self, mission_id, request):
        assert mission_id == "mission-1"
        assert request.observed_at == datetime(2026, 8, 16, tzinfo=UTC)
        return LocationResponse(
            status="GOING",
            instruction_code=InstructionCode.TURN_LEFT,
            message="앞에서 왼쪽으로 가세요.",
            vibration_hint=VibrationHint.LEFT,
            remaining_distance_m=80,
            off_route=False,
            wrong_way=False,
        )


class _Verifier:
    def verify(self, token, expected_role):
        if token == "child" and expected_role is MissionRole.CHILD:
            return RolePrincipal(mission_id="mission-1", role=MissionRole.CHILD)
        return None


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(locations.router)
    app.dependency_overrides[locations.get_location_service] = lambda: _LocationService()
    app.dependency_overrides[get_role_token_verifier] = lambda: _Verifier()
    return TestClient(app)


def test_location_endpoint_requires_the_matching_child_and_returns_guidance() -> None:
    client = _client()
    body = {
        "latitude": 37.56,
        "longitude": 126.97,
        "accuracy_m": 8,
        "heading_deg": 90,
        "observed_at": "2026-08-16T00:00:00Z",
    }

    forbidden = client.post(
        "/missions/other/locations", json=body, headers={"Authorization": "Bearer child"}
    )
    response = client.post(
        "/missions/mission-1/locations", json=body, headers={"Authorization": "Bearer child"}
    )

    assert forbidden.status_code == 403
    assert response.status_code == 200
    assert response.json() == {
        "instruction_code": "TURN_LEFT",
        "message": "앞에서 왼쪽으로 가세요.",
        "vibration_hint": "LEFT",
        "remaining_distance_m": 80.0,
        "off_route": False,
        "wrong_way": False,
        "status": "GOING",
    }
