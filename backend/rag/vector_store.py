from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Optional
from datetime import datetime
from backend.core.config import settings
from backend.rag.models import DocumentChunk, RetrievedChunk

# Helper to initialize client connection
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL, timeout=settings.TIMEOUT_QDRANT)

def ensure_collection():
    """
    Ensures that the vector collection exists on Qdrant startup.
    Creates it with 384 dimensions and COSINE distance matching metrics.
    """
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            print(f"Qdrant collection '{collection_name}' not found. Creating collection...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"Qdrant collection '{collection_name}' created successfully.")
        else:
            print(f"Qdrant collection '{collection_name}' already exists.")
    except Exception as e:
        print(f"Failed to check/create Qdrant collection: {e}")
        # Re-raise to flag connection failures on startup
        raise e

def upsert_chunks(chunks: List[DocumentChunk], vectors: List[List[float]]):
    """
    Batch upserts document text chunks and their corresponding embeddings
    into the Qdrant web_evidence collection.
    """
    if not chunks or not vectors or len(chunks) != len(vectors):
        print("Upsert skipped: empty chunks/vectors or dimension mismatch.")
        return
        
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION
    
    points = []
    for idx, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=chunk.id,  # Deterministic UUID string
            vector=vectors[idx],
            payload={
                "search_id": chunk.search_id,
                "subquery_id": chunk.subquery_id,
                "url": chunk.url,
                "title": chunk.title,
                "domain": chunk.domain,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "word_count": chunk.word_count,
                "created_at": datetime.utcnow().isoformat()
            }
        ))
        
    try:
        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )
        print(f"Successfully indexed {len(points)} chunks into Qdrant collection '{collection_name}'.")
    except Exception as e:
        print(f"Failed to upsert chunks to Qdrant: {e}")
        raise e

def search_similar(query_vector: List[float], search_id: int, top_k: int = 8) -> List[RetrievedChunk]:
    """
    Semantic similarity search on Qdrant:
    - Filters results using the metadata key 'search_id' to guarantee session isolation.
    - Returns similarity scores mapped to a list of RetrievedChunk objects.
    """
    if not query_vector:
        return []
        
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION
    
    # Session isolation filter criteria
    query_filter = Filter(
        must=[
            FieldCondition(
                key="search_id",
                match=MatchValue(value=search_id)
            )
        ]
    )
    
    try:
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k
        )
        
        hits = response.points
        retrieved = []
        for hit in hits:
            payload = hit.payload
            # Normalize Cosine similarity score to boundary range [0.0 - 1.0]
            norm_score = max(0.0, min(1.0, float(hit.score)))
            
            retrieved.append(RetrievedChunk(
                id=str(hit.id),
                search_id=payload.get("search_id"),
                subquery_id=payload.get("subquery_id"),
                url=payload.get("url"),
                title=payload.get("title", ""),
                domain=payload.get("domain", ""),
                chunk_index=payload.get("chunk_index", 0),
                text=payload.get("text", ""),
                score=norm_score
            ))
        return retrieved
    except Exception as e:
        print(f"Qdrant similarity search query failed: {e}")
        return []
        
def get_points_count() -> int:
    """Returns the total number of points stored in the active vector collection."""
    try:
        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION
        info = client.get_collection(collection_name=collection_name)
        return info.points_count or 0
    except Exception:
        return 0
