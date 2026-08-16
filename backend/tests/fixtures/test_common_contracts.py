from collections.abc import Callable
from typing import Annotated
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.dependencies import (
    RoleTokenVerifier,
    get_role_token_verifier,
    require_child,
    require_parent,
)
from app.core.config import REQUIRED_ENV_VARS, Settings, SettingsConfigurationError
from app.core.errors import AppError
from app.schemas.common import ErrorDetail, ErrorResponse, MissionRole, RolePrincipal


def test_settings_import_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.missing_required() == REQUIRED_ENV_VARS
    assert settings.app_env == "local"


def test_missing_required_settings_error_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    with pytest.raises(SettingsConfigurationError) as error:
        settings.require(*REQUIRED_ENV_VARS)

    assert error.value.code == "MISSING_REQUIRED_SETTINGS"
    assert list(REQUIRED_ENV_VARS) == error.value.missing
    assert ", ".join(REQUIRED_ENV_VARS) in error.value.message


def test_settings_reject_invalid_navigation_threshold() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, location_off_route_meters=0)


def test_common_error_schema_serializes_frozen_contract() -> None:
    response = ErrorResponse(
        error=ErrorDetail(code="MISSION_NOT_FOUND", message="미션이 없습니다.")
    )

    assert response.model_dump() == {
        "error": {"code": "MISSION_NOT_FOUND", "message": "미션이 없습니다."}
    }


@pytest.mark.anyio
async def test_app_error_uses_common_response(
    test_app: FastAPI,
    test_client: AsyncClient,
) -> None:
    @test_app.get("/conflict")
    def conflict() -> None:
        raise AppError(code="STATE_CONFLICT", message="상태를 전이할 수 없습니다.", status_code=409)

    response = await test_client.get("/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "STATE_CONFLICT", "message": "상태를 전이할 수 없습니다."}
    }


class FakeRoleTokenVerifier:
    def __init__(self, role: MissionRole) -> None:
        self.role = role
        self.calls: list[tuple[str, MissionRole]] = []

    def verify(self, token: str, expected_role: MissionRole) -> RolePrincipal | None:
        self.calls.append((token, expected_role))
        if expected_role is not self.role:
            return None
        return RolePrincipal(mission_id="mission-1", role=self.role)


def test_fake_role_verifier_matches_protocol() -> None:
    assert isinstance(FakeRoleTokenVerifier(MissionRole.PARENT), RoleTokenVerifier)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "dependency", "role"),
    [
        ("/parent-only", require_parent, MissionRole.PARENT),
        ("/child-only", require_child, MissionRole.CHILD),
    ],
)
async def test_role_dependency_can_be_overridden(
    test_app: FastAPI,
    test_client: AsyncClient,
    path: str,
    dependency: Callable[..., RolePrincipal],
    role: MissionRole,
) -> None:
    verifier = FakeRoleTokenVerifier(role)
    test_app.dependency_overrides[get_role_token_verifier] = lambda: verifier

    @test_app.get(path)
    def protected(principal: Annotated[RolePrincipal, Depends(dependency)]) -> dict[str, str]:
        return {"role": principal.role.value}

    response = await test_client.get(path, headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json() == {"role": role.value}
    assert verifier.calls == [("test-token", role)]


@pytest.mark.anyio
async def test_role_dependency_rejects_missing_bearer_token(
    test_app: FastAPI,
    test_client: AsyncClient,
) -> None:
    test_app.dependency_overrides[get_role_token_verifier] = lambda: FakeRoleTokenVerifier(
        MissionRole.PARENT
    )

    @test_app.get("/parent-only")
    def protected(
        principal: Annotated[RolePrincipal, Depends(require_parent)],
    ) -> dict[str, str]:
        return {"role": principal.role.value}

    response = await test_client.get("/parent-only")

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "AUTH_REQUIRED", "message": "Bearer token이 필요합니다."}
    }


def test_external_client_mocks_are_network_free(
    tmap_client_mock: object,
    openai_vision_client_mock: object,
) -> None:
    assert isinstance(tmap_client_mock, AsyncMock)
    assert isinstance(openai_vision_client_mock, AsyncMock)
