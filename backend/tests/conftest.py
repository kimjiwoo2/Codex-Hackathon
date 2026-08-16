import pytest


@pytest.fixture
def anyio_backend() -> str:
    """Run async integration tests on asyncio only."""
    return "asyncio"
