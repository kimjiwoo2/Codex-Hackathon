from pydantic import BaseModel, ConfigDict

from app.schemas.vision.common import RoadVisionResult


class RoadVisionResponse(BaseModel):
    """Safe, fixed child-facing road guidance without model-authored text."""

    model_config = ConfigDict(frozen=True)

    result: RoadVisionResult
    message: str
