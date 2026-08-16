from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InstructionCode(StrEnum):
    CONTINUE = "CONTINUE"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    CROSSWALK_STOP = "CROSSWALK_STOP"
    OFF_ROUTE = "OFF_ROUTE"
    WRONG_WAY = "WRONG_WAY"
    LOCATION_UNCERTAIN = "LOCATION_UNCERTAIN"
    ARRIVED = "ARRIVED"


class VibrationHint(StrEnum):
    NONE = "NONE"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STOP = "STOP"
    ALERT = "ALERT"
    ARRIVAL = "ARRIVAL"


class Guidance(BaseModel):
    """TTS-safe navigation result computed from the cached route only."""

    model_config = ConfigDict(frozen=True)

    instruction_code: InstructionCode
    message: str
    vibration_hint: VibrationHint
    remaining_distance_m: float = Field(ge=0)
    off_route: bool
    wrong_way: bool


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    speed_mps: float | None = Field(default=None, ge=0)
    observed_at: datetime


class LocationResponse(Guidance):
    status: str
