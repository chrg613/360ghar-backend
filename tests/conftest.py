"""
360Ghar Backend Test Suite - Main Configuration

This is the main conftest.py providing:
- PostgreSQL database fixtures with transaction rollback
- Authentication fixtures (user, agent, admin)
- Test client fixtures for API testing
- External service mocking setup
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.factory import create_app

# Import all models to ensure they're registered with SQLAlchemy
import app.models  # noqa: F401


# =============================================================================
# Configuration
# =============================================================================

# Test database URL - defaults to local PostgreSQL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://test_user:test_password@localhost:5432/test_db",
)

# Check if we're running in CI environment
IS_CI = os.getenv("CI", "false").lower() == "true"


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.

    This fixture is required for pytest-asyncio to work correctly
    with session-scoped async fixtures.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create the test database engine (session-scoped for performance).

    Creates all tables at the start of the test session and drops them
    at the end. Uses NullPool for compatibility with pgbouncer and
    to avoid connection pooling issues in tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )

    # Create all tables
    async with engine.begin() as conn:
        # Drop all tables first for a clean slate
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with automatic transaction rollback.

    Each test function gets its own session wrapped in a transaction
    that is rolled back at the end of the test, ensuring test isolation.
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        # Begin a transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when exiting the context


@pytest_asyncio.fixture(scope="function")
async def db(db_session) -> AsyncSession:
    """Alias for db_session for convenience."""
    return db_session


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_app(db_session: AsyncSession):
    """
    Create test application with overridden dependencies.

    Overrides the database dependency to use the test session,
    ensuring all database operations in tests use the same
    transaction that will be rolled back.
    """
    from app.core.database import get_db

    app = create_app()

    # Override database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    yield app

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for API testing.

    Uses httpx's ASGI transport to make requests directly to the
    application without needing a running server.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=30.0,
    ) as ac:
        yield ac


# =============================================================================
# Load Fixtures from Submodules
# =============================================================================

# Register fixture plugins from submodules
pytest_plugins = [
    "tests.fixtures.auth",
    "tests.fixtures.factories",
    "tests.fixtures.mocks",
    "tests.fixtures.data",
]
