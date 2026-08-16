from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Coordinate(BaseModel):
    """WGS84 coordinate shared by TMAP requests and normalized routes."""

    model_config = ConfigDict(frozen=True)

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class RoutePoint(Coordinate):
    """A route geometry point with distance measured from route start."""

    cumulative_distance_m: float = Field(ge=0)


class RouteStepKind(StrEnum):
    START = "START"
    STRAIGHT = "STRAIGHT"
    LEFT_TURN = "LEFT_TURN"
    RIGHT_TURN = "RIGHT_TURN"
    U_TURN = "U_TURN"
    CROSSWALK = "CROSSWALK"
    OVERPASS = "OVERPASS"
    UNDERPASS = "UNDERPASS"
    STAIRS = "STAIRS"
    RAMP = "RAMP"
    ELEVATOR = "ELEVATOR"
    ARRIVE = "ARRIVE"
    OTHER = "OTHER"


class RouteStep(BaseModel):
    """A normalized TMAP maneuver or pedestrian facility."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    kind: RouteStepKind
    coordinate: Coordinate
    cumulative_distance_m: float = Field(ge=0)
    description: str = ""
    turn_type: int | None = None
    facility_type: int | None = None
    is_crosswalk: bool = False
    is_stairs: bool = False


class Route(BaseModel):
    """Network-independent route contract consumed by mission and navigation services."""

    model_config = ConfigDict(frozen=True)

    total_distance_m: float = Field(gt=0)
    total_time_seconds: int = Field(ge=0)
    points: tuple[RoutePoint, ...] = Field(min_length=2)
    steps: tuple[RouteStep, ...] = Field(min_length=2)

    @property
    def geometry(self) -> tuple[RoutePoint, ...]:
        """Expose the flattened geometry while serialized storage keeps the `points` contract."""
        return self.points


class RoundTripRoutes(BaseModel):
    """Cached routes for the outbound mission and safe return home."""

    model_config = ConfigDict(frozen=True)

    outbound: Route
    returning: Route
