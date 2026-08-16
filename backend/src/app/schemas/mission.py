from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import MissionStatus
from app.schemas.navigation.route import Coordinate


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class _CamelCaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class MissionItemRequest(_CamelCaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    size: str | None = Field(default=None, max_length=100)


class CreateMissionRequest(_CamelCaseModel):
    home: Coordinate
    store: Coordinate
    items: list[MissionItemRequest] = Field(min_length=1, max_length=20)


class CreateMissionResponse(_CamelCaseModel):
    mission_id: str
    join_code: str = Field(pattern=r"^\d{6}$")
    join_code_expires_at: str
    parent_token: str


class JoinMissionRequest(_CamelCaseModel):
    join_code: str = Field(pattern=r"^\d{6}$")


class JoinMissionResponse(_CamelCaseModel):
    mission_id: str
    child_token: str
    status: Literal[MissionStatus.GOING]
    instruction_code: str
    message: str


class ReturnHomeResponse(_CamelCaseModel):
    status: Literal[MissionStatus.RETURNING]
    return_strategy: Literal["RETRACE_OUTBOUND_FROM_PROGRESS", "USE_CACHED_RETURN_ROUTE"]
    outbound_progress_m: float = Field(ge=0)
