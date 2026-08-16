import pytest
from pydantic import ValidationError

from app.schemas.health import HealthResponse


def test_health_response_accepts_ready_status() -> None:
    response = HealthResponse(status="ok")

    assert response.model_dump() == {"status": "ok"}


def test_health_response_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        HealthResponse(status="unavailable")
