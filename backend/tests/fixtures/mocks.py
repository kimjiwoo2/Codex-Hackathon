from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def tmap_client_mock() -> AsyncMock:
    """Provide a configurable TMAP adapter double that never performs HTTP calls."""
    client = AsyncMock(name="tmap_client")
    client.get_round_trip.return_value = {
        "outbound": {"points": []},
        "returning": {"points": []},
    }
    return client


@pytest.fixture
def openai_vision_client_mock() -> AsyncMock:
    """Provide a configurable OpenAI vision adapter double without SDK calls."""
    client = AsyncMock(name="openai_vision_client")
    client.analyze_road.return_value = {"result": "UNKNOWN"}
    client.analyze_product.return_value = {"result": "UNKNOWN"}
    return client
