from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import ApplicationComponents, create_app

pytest_plugins = ["tests.fixtures.mocks"]


@pytest.fixture
def anyio_backend() -> str:
    """Run async integration tests on asyncio only."""
    return "asyncio"


@pytest.fixture
def app_factory() -> Callable[[], FastAPI]:
    """Build isolated applications so dependency overrides never leak between tests."""
    return create_app


@pytest.fixture
def test_app(app_factory: Callable[[], FastAPI]) -> FastAPI:
    """Provide the shared application boundary without external dependencies."""
    return app_factory()


@pytest.fixture
def composed_app_factory() -> Callable[[ApplicationComponents], FastAPI]:
    """Exercise the real create_app router path with a prebuilt test composition graph."""

    def factory(components: ApplicationComponents) -> FastAPI:
        return create_app(settings=components.settings, components=components)

    return factory


@pytest.fixture
async def test_client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Call the ASGI application in-process without opening a network socket."""
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
