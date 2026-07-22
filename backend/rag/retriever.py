from typing import List
from backend.rag.models import RetrievedChunk
from backend.rag.embeddings import embed_text
from backend.rag.vector_store import search_similar

async def retrieve_evidence(query: str, search_id: int, top_k: int = 8) -> List[RetrievedChunk]:
    """
    Translates user search query strings into normalized vectors
    and queries the Qdrant database with strict search_id filter boundaries.
    """
    # Enforce safe parameter bounds
    bounded_k = max(1, min(20, top_k))
    
    if not query.strip():
        return []
        
    try:
        # 1. Generate query embedding vector
        query_vector = embed_text(query.strip())
        if not query_vector:
            print("Aborting retrieval: query embedding vector generation failed.")
            return []
            
        # 2. Search vector store using metadata query filters for isolation
        results = search_similar(query_vector, search_id, top_k=bounded_k)
        return results
    except Exception as e:
        print(f"Retrieval query execution failed for search_id={search_id}: {e}")
        return []
