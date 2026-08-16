import re

import pytest

from app.schemas.common import MissionRole
from app.security.roles import MissionRoleTokenVerifier
from app.security.tokens import (
    generate_join_code,
    generate_opaque_token,
    hash_join_code,
    hash_opaque_token,
    hash_secret,
    verify_join_code,
    verify_opaque_token,
    verify_secret,
)


class RepositoryThatMustNotBeCalled:
    def find_mission_id_by_role_token_hash(self, encoded_hash: str, role: MissionRole) -> str:
        raise AssertionError("invalid token must not reach the repository")


@pytest.mark.parametrize("token", ["", " ", "too-short", "!" * 43, "a" * 44])
def test_role_verifier_rejects_malformed_opaque_tokens_without_raising(token: str) -> None:
    verifier = MissionRoleTokenVerifier(RepositoryThatMustNotBeCalled())

    assert verifier.verify(token, MissionRole.PARENT) is None


def test_join_code_is_exactly_six_digits() -> None:
    codes = {generate_join_code() for _ in range(32)}

    assert all(re.fullmatch(r"\d{6}", code) for code in codes)
    assert len(codes) > 1


def test_opaque_token_has_at_least_256_bits_of_random_input() -> None:
    token = generate_opaque_token()

    assert len(token) >= 43
    assert token != generate_opaque_token()


def test_secret_hash_is_salted_and_verifiable_without_plaintext() -> None:
    secret = "123456"

    first = hash_secret(secret)
    second = hash_secret(secret)

    assert first != second
    assert secret not in first
    assert verify_secret(secret, first)
    assert not verify_secret("654321", first)
    assert not verify_secret(secret, "invalid-hash")


def test_join_code_hash_rejects_values_outside_public_contract() -> None:
    encoded_hash = hash_join_code("012345")

    assert verify_join_code("012345", encoded_hash)
    assert not verify_join_code("12345", encoded_hash)
    with pytest.raises(ValueError):
        hash_join_code("12345A")


def test_high_entropy_opaque_token_uses_stable_lookup_hash() -> None:
    token = generate_opaque_token()

    encoded_hash = hash_opaque_token(token)

    assert encoded_hash == hash_opaque_token(token)
    assert token not in encoded_hash
    assert verify_opaque_token(token, encoded_hash)
    assert not verify_opaque_token(generate_opaque_token(), encoded_hash)
