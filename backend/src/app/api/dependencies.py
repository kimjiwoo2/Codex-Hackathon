from typing import Annotated, Protocol, runtime_checkable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.schemas.common import MissionRole, RolePrincipal

_bearer_scheme = HTTPBearer(auto_error=False)


@runtime_checkable
class RoleTokenVerifier(Protocol):
    """Boundary implemented by the security layer and replaceable in API tests."""

    def verify(self, token: str, expected_role: MissionRole) -> RolePrincipal | None: ...


def get_role_token_verifier() -> RoleTokenVerifier:
    """Require feature assembly to provide the concrete token verifier."""
    raise AppError(
        code="AUTH_DEPENDENCY_NOT_CONFIGURED",
        message="인증 의존성이 구성되지 않았습니다.",
        status_code=503,
    )


Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]
Verifier = Annotated[RoleTokenVerifier, Depends(get_role_token_verifier)]


def _require_role(
    credentials: HTTPAuthorizationCredentials | None,
    verifier: RoleTokenVerifier,
    role: MissionRole,
) -> RolePrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            code="AUTH_REQUIRED",
            message="Bearer token이 필요합니다.",
            status_code=401,
        )

    principal = verifier.verify(credentials.credentials, role)
    if principal is None or principal.role is not role:
        raise AppError(
            code="AUTH_FORBIDDEN",
            message="이 작업을 수행할 권한이 없습니다.",
            status_code=403,
        )
    return principal


def require_parent(credentials: Credentials, verifier: Verifier) -> RolePrincipal:
    """Resolve and enforce a parent mission token."""
    return _require_role(credentials, verifier, MissionRole.PARENT)


def require_child(credentials: Credentials, verifier: Verifier) -> RolePrincipal:
    """Resolve and enforce a child mission token."""
    return _require_role(credentials, verifier, MissionRole.CHILD)
