import base64
import json
from typing import Any, Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

import openai
from app.schemas.vision.common import ProductVisionAnalysis, RoadVisionAnalysis
from openai import AsyncOpenAI

VISION_TIMEOUT_SECONDS = 8.0

AnalysisT = TypeVar("AnalysisT", bound=BaseModel)


class _Responses(Protocol):
    async def parse(self, **kwargs: Any) -> object: ...


class _AsyncOpenAI(Protocol):
    responses: _Responses

    def with_options(self, **kwargs: Any) -> "_AsyncOpenAI": ...


class VisionUnavailable(RuntimeError):
    """Represent any OpenAI transport or structured-output failure without raw details."""

    code = "VISION_UNAVAILABLE"

    def __init__(self) -> None:
        super().__init__("비전 분석을 사용할 수 없습니다")


class OpenAIVisionClient:
    """Shared Responses API boundary for road and product image analysis."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        client: _AsyncOpenAI | None = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("api_key is required when client is not provided")
            client = cast(_AsyncOpenAI, AsyncOpenAI(api_key=api_key))

        self._model = model
        self._responses = client.with_options(
            timeout=VISION_TIMEOUT_SECONDS,
            max_retries=0,
        ).responses

    async def analyze_road(self, image: bytes) -> RoadVisionAnalysis:
        return await self._analyze(
            image=image,
            detail="low",
            prompt=(
                "Inspect this road scene for visible hazards. "
                "Never state that crossing is safe. Return the structured result only."
            ),
            text_format=RoadVisionAnalysis,
        )

    async def analyze_product(
        self,
        image: bytes,
        *,
        name: str,
        brand: str | None = None,
        size: str | None = None,
    ) -> ProductVisionAnalysis:
        criteria = json.dumps(
            {"name": name, "brand": brand, "size": size},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return await self._analyze(
            image=image,
            detail="high",
            prompt=(
                "Compare the pictured product with these requested attributes: "
                f"{criteria}. Return the structured result only."
            ),
            text_format=ProductVisionAnalysis,
        )

    async def _analyze(
        self,
        *,
        image: bytes,
        detail: str,
        prompt: str,
        text_format: type[AnalysisT],
    ) -> AnalysisT:
        image_url = f"data:image/jpeg;base64,{base64.b64encode(image).decode('ascii')}"
        try:
            response = await self._responses.parse(
                model=self._model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": image_url,
                                "detail": detail,
                            },
                        ],
                    }
                ],
                text_format=text_format,
                store=False,
            )
            parsed = getattr(response, "output_parsed", None)
        except (openai.OpenAIError, ValidationError, ValueError):
            raise VisionUnavailable from None

        if not isinstance(parsed, text_format):
            raise VisionUnavailable
        return parsed
