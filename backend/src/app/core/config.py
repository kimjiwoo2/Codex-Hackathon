from functools import lru_cache
from typing import Final, Self

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import AppError

REQUIRED_ENV_VARS: Final[tuple[str, ...]] = (
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "TMAP_APP_KEY",
)
OPTIONAL_ENV_VARS: Final[tuple[str, ...]] = (
    "APP_ENV",
    "CORS_ALLOW_ORIGINS",
    "DATABASE_URL_DIRECT",
    "LOCATION_EVENT_COOLDOWN_SECONDS",
    "LOCATION_OFF_ROUTE_METERS",
    "LOCATION_WRONG_WAY_DEGREES",
    "MISSION_JOIN_CODE_TTL_MINUTES",
    "OPENAI_VISION_MODEL",
)

_ENV_TO_FIELD: Final[dict[str, str]] = {
    "APP_ENV": "app_env",
    "CORS_ALLOW_ORIGINS": "cors_allow_origins",
    "DATABASE_URL": "database_url",
    "DATABASE_URL_DIRECT": "database_url_direct",
    "LOCATION_EVENT_COOLDOWN_SECONDS": "location_event_cooldown_seconds",
    "LOCATION_OFF_ROUTE_METERS": "location_off_route_meters",
    "LOCATION_WRONG_WAY_DEGREES": "location_wrong_way_degrees",
    "MISSION_JOIN_CODE_TTL_MINUTES": "mission_join_code_ttl_minutes",
    "OPENAI_API_KEY": "openai_api_key",
    "OPENAI_VISION_MODEL": "openai_vision_model",
    "TMAP_APP_KEY": "tmap_app_key",
}


class SettingsConfigurationError(AppError):
    """Report missing runtime configuration without exposing configured secrets."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            code="MISSING_REQUIRED_SETTINGS",
            message=f"필수 환경 변수가 누락되었습니다: {', '.join(missing)}",
            status_code=503,
        )


class Settings(BaseSettings):
    """Environment-backed settings whose import never requires secret values."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=None,
        env_prefix="",
        extra="ignore",
    )

    app_env: str = "local"
    cors_allow_origins: str = "http://localhost:8081,http://127.0.0.1:8081"

    database_url: SecretStr | None = None
    database_url_direct: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_vision_model: str = "gpt-5.6-luna"
    tmap_app_key: SecretStr | None = None

    location_off_route_meters: float = Field(default=30, gt=0)
    location_wrong_way_degrees: float = Field(default=120, gt=0, le=180)
    location_event_cooldown_seconds: int = Field(default=30, ge=0)
    mission_join_code_ttl_minutes: int = Field(default=180, gt=0)

    @property
    def cors_origins(self) -> tuple[str, ...]:
        """Normalize the comma-separated environment value for FastAPI middleware."""
        return tuple(
            origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()
        )

    def missing_required(self, names: tuple[str, ...] = REQUIRED_ENV_VARS) -> tuple[str, ...]:
        """Return required environment names that have no non-empty value."""
        unknown = [name for name in names if name not in _ENV_TO_FIELD]
        if unknown:
            raise ValueError(f"알 수 없는 필수 환경 변수입니다: {', '.join(unknown)}")

        return tuple(
            name for name in names if not _has_secret_value(getattr(self, _ENV_TO_FIELD[name]))
        )

    def require(self, *names: str) -> Self:
        """Validate an adapter's required settings only when that adapter is used."""
        required_names = tuple(names) if names else REQUIRED_ENV_VARS
        missing = self.missing_required(required_names)
        if missing:
            raise SettingsConfigurationError(list(missing))
        return self


def _has_secret_value(value: object) -> bool:
    if isinstance(value, SecretStr):
        return bool(value.get_secret_value().strip())
    return bool(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load process settings once; tests may override this FastAPI dependency."""
    return Settings()
