from pydantic import BaseModel, ConfigDict, Field

from app.models import ItemVerdict, MissionStatus


class ItemVerificationResponse(BaseModel):
    """Safe product-verification result for the child application to read aloud."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    verdict: ItemVerdict
    message: str = Field(min_length=1, max_length=100)
    detected_label: str | None = Field(default=None, alias="detectedLabel", max_length=300)
    status: MissionStatus
