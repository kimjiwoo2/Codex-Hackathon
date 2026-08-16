import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx2
import openai
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.integrations.openai import OpenAIVisionClient, VisionUnavailable
from app.schemas.vision.common import (
    ProductVisionAnalysis,
    ProductVisionResult,
    RoadVisionAnalysis,
    RoadVisionResult,
)

FIXTURES = Path(__file__).parents[2] / "fixtures" / "openai"


class FakeResponses:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        text_format: type[BaseModel] = kwargs["text_format"]
        return SimpleNamespace(output_parsed=text_format.model_validate_json(self.payload))


class FakeAsyncOpenAI:
    def __init__(self, responses: object) -> None:
        self.responses = responses
        self.options: dict[str, Any] | None = None

    def with_options(self, **kwargs: Any) -> "FakeAsyncOpenAI":
        self.options = kwargs
        return self


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.mark.anyio
async def test_analyze_road_uses_low_detail_and_parses_structured_fixture() -> None:
    responses = FakeResponses(fixture_text("road_response.json"))
    sdk = FakeAsyncOpenAI(responses)
    client = OpenAIVisionClient(model="gpt-test", client=sdk)

    result = await client.analyze_road(b"jpeg-road")

    assert result == RoadVisionAnalysis(
        result=RoadVisionResult.CAUTION,
        detected_label="parked car near curb",
        description="A parked car may block the view of the road.",
    )
    assert sdk.options == {"timeout": 8.0, "max_retries": 0}
    call = responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["text_format"] is RoadVisionAnalysis
    assert call["store"] is False
    content = call["input"][0]["content"]
    assert content[1] == {
        "type": "input_image",
        "image_url": "data:image/jpeg;base64,anBlZy1yb2Fk",
        "detail": "low",
    }


@pytest.mark.anyio
async def test_official_sdk_serializes_image_and_json_schema_without_network() -> None:
    captured: dict[str, Any] = {}

    async def handler(request: httpx2.Request) -> httpx2.Response:
        captured.update(json.loads(request.content))
        return httpx2.Response(
            200,
            request=request,
            json={
                "id": "resp_test",
                "created_at": 0.0,
                "model": "gpt-test",
                "object": "response",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": fixture_text("road_response.json"),
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "status": "completed",
            },
        )

    http_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    sdk = AsyncOpenAI(
        api_key="test-key",
        base_url="https://openai.invalid/v1",
        http_client=http_client,
    )
    client = OpenAIVisionClient(model="gpt-test", client=sdk)

    try:
        result = await client.analyze_road(b"jpeg-road")
    finally:
        await http_client.aclose()

    assert result.result is RoadVisionResult.CAUTION
    assert captured["store"] is False
    assert captured["text"]["format"]["type"] == "json_schema"
    content = captured["input"][0]["content"]
    assert content[1]["detail"] == "low"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


@pytest.mark.anyio
async def test_analyze_product_uses_high_detail_and_product_criteria() -> None:
    responses = FakeResponses(fixture_text("product_response.json"))
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    result = await client.analyze_product(
        b"jpeg-product",
        name="Milk",
        brand="Seoul Milk",
        size="1L",
    )

    assert result.result is ProductVisionResult.MATCH
    call = responses.calls[0]
    assert call["text_format"] is ProductVisionAnalysis
    content = call["input"][0]["content"]
    assert content[1]["detail"] == "high"
    prompt = content[0]["text"]
    assert all(value in prompt for value in ("Milk", "Seoul Milk", "1L"))


@pytest.mark.anyio
async def test_timeout_becomes_safe_vision_unavailable() -> None:
    responses = SimpleNamespace(
        parse=AsyncMock(
            side_effect=openai.APITimeoutError(
                request=httpx2.Request("POST", "https://openai.invalid/v1/responses")
            )
        )
    )
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    with pytest.raises(VisionUnavailable, match="비전 분석을 사용할 수 없습니다") as exc_info:
        await client.analyze_road(b"secret-image")

    assert exc_info.value.__cause__ is None
    assert "secret-image" not in str(exc_info.value)


@pytest.mark.anyio
async def test_sdk_error_becomes_safe_vision_unavailable() -> None:
    sdk_error = openai.APIError("raw model response", request=None, body="private body")
    responses = SimpleNamespace(parse=AsyncMock(side_effect=sdk_error))
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    with pytest.raises(VisionUnavailable) as exc_info:
        await client.analyze_product(b"secret-image", name="Milk")

    assert exc_info.value.__cause__ is None
    assert "raw model response" not in str(exc_info.value)
    assert "private body" not in str(exc_info.value)


@pytest.mark.anyio
async def test_invalid_structured_output_becomes_vision_unavailable() -> None:
    responses = FakeResponses(fixture_text("invalid_response.json"))
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    with pytest.raises(VisionUnavailable):
        await client.analyze_road(b"jpeg-road")


@pytest.mark.anyio
async def test_missing_parsed_output_becomes_vision_unavailable() -> None:
    responses = SimpleNamespace(parse=AsyncMock(return_value=SimpleNamespace(output_parsed=None)))
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    with pytest.raises(VisionUnavailable):
        await client.analyze_road(b"jpeg-road")


@pytest.mark.anyio
async def test_adapter_does_not_log_image_or_raw_model_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_text = "raw-model-text-that-must-not-leak"
    responses = SimpleNamespace(
        parse=AsyncMock(side_effect=openai.APIError(raw_text, request=None, body=raw_text))
    )
    client = OpenAIVisionClient(
        model="gpt-test",
        client=FakeAsyncOpenAI(responses),
    )

    with pytest.raises(VisionUnavailable):
        await client.analyze_road(b"image-bytes-that-must-not-leak")

    assert raw_text not in caplog.text
    assert "image-bytes-that-must-not-leak" not in caplog.text
    assert "aW1hZ2UtYnl0ZXMtdGhhdC1tdXN0LW5vdC1sZWFr" not in caplog.text


def test_fixture_keys_use_public_aliases() -> None:
    payload = json.loads(fixture_text("product_response.json"))

    assert set(payload) == {"result", "detectedLabel", "description"}
