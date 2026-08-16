import base64
import hashlib
import hmac
import secrets
from typing import Final

_ALGORITHM: Final = "pbkdf2_sha256"
_ITERATIONS: Final = 210_000
_SALT_BYTES: Final = 16
_TOKEN_BYTES: Final = 32


def generate_join_code() -> str:
    """Return a zero-padded six-digit code using a cryptographic RNG."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_opaque_token() -> str:
    """Return a URL-safe opaque token backed by 256 random bits."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_join_code(join_code: str) -> str:
    """Hash a validated six-digit join code with a per-value random salt."""
    if len(join_code) != 6 or not join_code.isdigit():
        raise ValueError("join code must contain exactly six digits")
    return hash_secret(join_code)


def verify_join_code(join_code: str, encoded_hash: str) -> bool:
    """Verify only values that satisfy the public join-code shape."""
    return len(join_code) == 6 and join_code.isdigit() and verify_secret(join_code, encoded_hash)


def hash_opaque_token(token: str) -> str:
    """Return a stable lookup hash for a token carrying 256 bits of entropy."""
    if not token:
        raise ValueError("token must not be empty")
    return f"sha256${hashlib.sha256(token.encode()).hexdigest()}"


def verify_opaque_token(token: str, encoded_hash: str) -> bool:
    """Compare an opaque token with its lookup hash in constant time."""
    try:
        algorithm, _digest = encoded_hash.split("$", 1)
    except (AttributeError, ValueError):
        return False
    if algorithm != "sha256":
        return False
    return hmac.compare_digest(hash_opaque_token(token), encoded_hash)


def hash_secret(secret: str) -> str:
    """Encode a salted one-way hash suitable for join codes and role tokens."""
    if not secret:
        raise ValueError("secret must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, _ITERATIONS)
    return "$".join((_ALGORITHM, str(_ITERATIONS), _encode(salt), _encode(digest)))


def verify_secret(secret: str, encoded_hash: str) -> bool:
    """Verify malformed or mismatching values without raising or leaking details."""
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = encoded_hash.split("$", 3)
        iterations = int(raw_iterations)
        if algorithm != _ALGORITHM or iterations != _ITERATIONS:
            return False
        salt = _decode(raw_salt)
        expected = _decode(raw_digest)
    except (TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding, altchars=b"-_", validate=True)
