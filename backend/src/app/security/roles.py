from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

from app.schemas.common import MissionRole, RolePrincipal
from app.security.tokens import hash_opaque_token, is_valid_opaque_token, verify_join_code


class SecretHashCandidate(Protocol):
    mission_id: str
    encoded_hash: str


class MissionCredentialRepository(Protocol):
    def find_mission_id_by_role_token_hash(
        self,
        encoded_hash: str,
        role: MissionRole,
    ) -> str | None: ...

    def list_join_code_candidates(
        self,
        *,
        now: datetime | None = None,
    ) -> Iterable[SecretHashCandidate]: ...


class MissionRoleTokenVerifier:
    """Resolve an opaque role token without exposing or persisting its plaintext."""

    def __init__(self, repository: MissionCredentialRepository) -> None:
        self._repository = repository

    def verify(self, token: str, expected_role: MissionRole) -> RolePrincipal | None:
        if not is_valid_opaque_token(token):
            return None
        mission_id = self._repository.find_mission_id_by_role_token_hash(
            hash_opaque_token(token), expected_role
        )
        if mission_id is None:
            return None
        return RolePrincipal(mission_id=mission_id, role=expected_role)


class MissionJoinCodeVerifier:
    """Resolve an active six-digit join code from salted database hashes."""

    def __init__(self, repository: MissionCredentialRepository) -> None:
        self._repository = repository

    def find_mission_id(self, join_code: str, *, now: datetime | None = None) -> str | None:
        if len(join_code) != 6 or not join_code.isdigit():
            return None
        checked_at = now or datetime.now(UTC)
        matches = [
            candidate
            for candidate in self._repository.list_join_code_candidates(now=checked_at)
            if verify_join_code(join_code, candidate.encoded_hash)
        ]
        if len(matches) != 1:
            return None
        return matches[0].mission_id
