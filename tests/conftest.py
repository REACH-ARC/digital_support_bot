import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.db.base import Base
from app.core.config import settings
from app.main import app
from httpx import AsyncClient, ASGITransport

# Use an in-memory SQLite database for tests for simplicity validation
# OR easier: mock the session.
# But for "production quality" we usually want real DB tests or at least SQLite with SQLAlchmey
# Since our code uses PostgreSQL specific UUIDs, SQLite might fail on specific PG types.
# We will assume the user spins up a test DB or we mock the session.
# To keep it runnable without a real PG instance, let's mock the session for unit tests,
# or try to use sqlite with some hacks.
# 
# ACTUALLY: The "User" model uses `sqlalchemy.dialects.postgresql.UUID`. This will fail on SQLite.
# We should recommend running compliance tests against the docker container.
# For now, let's write tests that mock the DB interaction or use a "TestClient" that overrides the dependency.

from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async client for FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# Mock Session Fixture
@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncSession)
    return session
