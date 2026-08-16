from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Machine-readable code and safe user-facing message for an API failure."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ErrorResponse(BaseModel):
    """Envelope shared by every handled API error."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetail


class MissionRole(StrEnum):
    PARENT = "parent"
    CHILD = "child"


class RolePrincipal(BaseModel):
    """Verified mission identity passed from HTTP dependencies to endpoints."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(min_length=1)
    role: MissionRole
