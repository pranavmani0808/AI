from qdrant_client import QdrantClient
from backend.core.config import settings
from urllib.parse import urlparse

async def check_qdrant_health() -> bool:
    """Verifies that the Qdrant service is reachable via TCP/HTTP connection."""
    try:
        # Parse the Qdrant URL to extract host and port details
        parsed = urlparse(settings.QDRANT_URL)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333
        
        # Use QdrantClient to check server readiness without initializing collections
        client = QdrantClient(host=host, port=port, timeout=2.0)
        # Check if the service is running
        status = client.info()
        return status is not None
    except Exception as e:
        print(f"Qdrant health check connection error: {e}")
        return False
