import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop to prevent 'Event loop is closed' errors during test teardowns."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
