import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock

from backend.main import app
from backend.observability.logger import redact_secrets
from backend.core.errors import ErrorCategory, USER_ERROR_MESSAGES

class MockDBResult:
    def __init__(self, scalar_val=None, scalars_list=None, fetchone_val=None):
        self._scalar_val = scalar_val
        self._scalars_list = scalars_list or []
        self._fetchone_val = fetchone_val

    def scalar(self):
        return self._scalar_val

    def fetchone(self):
        return self._fetchone_val

    def scalars(self):
        class MockScalars:
            def __init__(self, lst):
                self.lst = lst
            def all(self):
                return self.lst
        return MockScalars(self._scalars_list)

@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verifies that the /health status API returns active states."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "postgres" in data["services"]
        assert "redis" in data["services"]

@pytest.mark.asyncio
async def test_readiness_check_endpoint():
    """Verifies readiness checks configurations and collection presence."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

@pytest.mark.asyncio
async def test_request_size_limits():
    """Verifies that queries exceeding 4000 characters are rejected with HTTP 422."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        long_query = "A" * 4001
        response = await client.post("/api/research/autonomous", json={"query": long_query})
        assert response.status_code == 422
        assert "detail" in response.json()

def test_secret_logging_redaction():
    """Verifies that logging redact_secrets sanitizes Gemini API keys and HF tokens."""
    gemini_key = "my key is AIzaSyTestKeyForRedactionTesting1234567890"
    hf_token = "my token is hf_TestTokenForRedactionTesting1234567890"
    
    redacted_gemini = redact_secrets(gemini_key)
    redacted_hf = redact_secrets(hf_token)
    
    assert "[REDACTED_SECRET]" in redacted_gemini
    assert "AIzaSyTestKey" not in redacted_gemini
    
    assert "[REDACTED_SECRET]" in redacted_hf
    assert "hf_TestToken" not in redacted_hf

def test_error_classification_mappings():
    """Verifies that core error categories resolve to safe user messages."""
    assert ErrorCategory.SEARCH_FAILED in USER_ERROR_MESSAGES
    assert ErrorCategory.QDRANT_UNAVAILABLE in USER_ERROR_MESSAGES
    assert "metasearch" in USER_ERROR_MESSAGES[ErrorCategory.SEARCH_FAILED].lower()

@pytest.mark.asyncio
async def test_metrics_summary_endpoint(monkeypatch):
    """Verifies retrieval of aggregate research analytics summaries with mocked db."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = [
        MockDBResult(scalar_val=0), # total count
        MockDBResult(scalar_val=0), # success count
        MockDBResult(scalar_val=0), # failed count
        MockDBResult(fetchone_val=(0, 0.0, 0.0)) # averages
    ]
    
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    monkeypatch.setattr("backend.api.research.AsyncSessionLocal", mock_session_local)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/research/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_searches" in data
        assert "successful_searches" in data
        assert "average_response_ms" in data

@pytest.mark.asyncio
async def test_history_list_endpoint(monkeypatch):
    """Verifies session history listing route with mocked db."""
    mock_session = AsyncMock()
    mock_session.execute.return_value = MockDBResult(scalars_list=[])
    
    mock_session_local = MagicMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    monkeypatch.setattr("backend.api.research.AsyncSessionLocal", mock_session_local)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/research/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
