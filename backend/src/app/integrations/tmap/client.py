from urllib.parse import quote

import httpx

from app.core.config import Settings
from app.integrations.tmap.errors import TmapUnavailable
from app.integrations.tmap.normalizer import normalize_route
from app.schemas.navigation.route import Coordinate, RoundTripRoutes, Route

TMAP_PEDESTRIAN_URL = "https://apis.openapi.sk.com/tmap/routes/pedestrian"


class TmapClient:
    """Async boundary for TMAP pedestrian routes with a bounded request timeout."""

    def __init__(
        self,
        *,
        app_key: str,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        if not app_key.strip():
            raise ValueError("app_key must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._app_key = app_key
        self._http_client = http_client
        self._timeout = httpx.Timeout(timeout_seconds)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 8.0,
    ) -> "TmapClient":
        settings.require("TMAP_APP_KEY")
        app_key = settings.tmap_app_key
        if app_key is None:
            raise AssertionError("validated TMAP_APP_KEY is missing")
        return cls(
            app_key=app_key.get_secret_value(),
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    async def get_pedestrian_route(
        self,
        start: Coordinate,
        end: Coordinate,
        *,
        start_name: str = "출발지",
        end_name: str = "도착지",
    ) -> Route:
        payload = {
            "angle": 0,
            "speed": 0,
            "reqCoordType": "WGS84GEO",
            "searchOption": "0",
            "resCoordType": "WGS84GEO",
            "sort": "index",
            "startX": start.longitude,
            "startY": start.latitude,
            "endX": end.longitude,
            "endY": end.latitude,
            "startName": quote(start_name, safe=""),
            "endName": quote(end_name, safe=""),
        }
        response = await self._post(payload)
        try:
            return normalize_route(response.json())
        except (ValueError, TypeError) as error:
            raise TmapUnavailable() from error

    async def get_round_trip(
        self,
        home: Coordinate,
        destination: Coordinate,
        *,
        home_name: str = "집",
        destination_name: str = "마트",
    ) -> RoundTripRoutes:
        outbound = await self.get_pedestrian_route(
            home,
            destination,
            start_name=home_name,
            end_name=destination_name,
        )
        returning = await self.get_pedestrian_route(
            destination,
            home,
            start_name=destination_name,
            end_name=home_name,
        )
        return RoundTripRoutes(outbound=outbound, returning=returning)

    async def _post(self, payload: dict[str, object]) -> httpx.Response:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "appKey": self._app_key,
        }
        try:
            if self._http_client is not None:
                response = await self._http_client.post(
                    TMAP_PEDESTRIAN_URL,
                    params={"version": "1"},
                    headers=headers,
                    json=payload,
                    timeout=self._timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as http_client:
                    response = await http_client.post(
                        TMAP_PEDESTRIAN_URL,
                        params={"version": "1"},
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            raise TmapUnavailable() from error
