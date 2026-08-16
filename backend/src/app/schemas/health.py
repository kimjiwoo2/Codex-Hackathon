from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response body returned by the service availability endpoint."""

    status: Literal["ok"]
