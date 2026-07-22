from typing import List
from backend.core.config import settings
from backend.rag.models import RetrievedChunk
from backend.rag.embeddings import embed_text
from backend.rag.vector_store import search_similar

async def retrieve_evidence(query: str, search_id: int, top_k: int = 8, min_score: float = None) -> List[RetrievedChunk]:
    """
    Translates user search query strings into normalized vectors,
    queries Qdrant vector store with search_id isolation filters,
    and filters out weak chunks below min_score threshold.
    """
    threshold = min_score if min_score is not None else settings.RAG_MIN_SCORE
    bounded_k = max(1, min(20, top_k))
    
    if not query.strip():
        return []
        
    try:
        # 1. Generate query embedding vector
        query_vector = embed_text(query.strip())
        if not query_vector:
            print("Aborting retrieval: query embedding vector generation failed.")
            return []
            
        # 2. Search vector store using metadata query filters
        results = search_similar(query_vector, search_id, top_k=bounded_k)
        
        # 3. Filter out weak chunks below configurable similarity threshold
        filtered_results = [r for r in results if r.score >= threshold]
        
        if len(results) > len(filtered_results):
            print(f"Similarity Threshold Filter: Kept {len(filtered_results)}/{len(results)} chunks meeting min_score >= {threshold}")
            
        return filtered_results
    except Exception as e:
        print(f"Retrieval query execution failed for search_id={search_id}: {e}")
        return []
