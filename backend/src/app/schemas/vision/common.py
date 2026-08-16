from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RoadVisionResult(StrEnum):
    STOP = "STOP"
    CAUTION = "CAUTION"
    UNKNOWN = "UNKNOWN"


class ProductVisionResult(StrEnum):
    MATCH = "MATCH"
    SIMILAR = "SIMILAR"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class VisionAnalysis(BaseModel):
    """Normalized fields safe for services to consume without SDK response objects."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    detected_label: str | None = Field(default=None, alias="detectedLabel", max_length=120)
    description: str = Field(min_length=1, max_length=300)


class RoadVisionAnalysis(VisionAnalysis):
    result: RoadVisionResult


class ProductVisionAnalysis(VisionAnalysis):
    result: ProductVisionResult
