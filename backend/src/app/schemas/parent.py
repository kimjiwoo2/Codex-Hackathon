from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import ItemVerdict, MissionEventType, MissionStatus


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class _CamelCaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class ParentLocation(_CamelCaseModel):
    latitude: float
    longitude: float
    observed_at: datetime
    accuracy_m: float | None = Field(default=None, ge=0)


class ParentItem(_CamelCaseModel):
    item_id: str
    name: str
    verdict: ItemVerdict
    detected_label: str | None = None
    verified_at: datetime | None = None


class ParentEvent(_CamelCaseModel):
    event_id: int = Field(ge=1)
    event_type: MissionEventType
    payload: dict[str, Any]
    created_at: datetime


class ParentSnapshotResponse(_CamelCaseModel):
    mission_id: str
    status: MissionStatus
    location: ParentLocation | None
    location_stale: bool
    remaining_distance_m: float = Field(ge=0)
    items: tuple[ParentItem, ...]
    events: tuple[ParentEvent, ...]
    next_event_id: int = Field(ge=0)
