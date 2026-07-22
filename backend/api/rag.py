from fastapi import APIRouter, HTTPException, status
from backend.rag.models import RetrievalRequest, RetrievalResponse
from backend.rag.pipeline import run_retrieval_pipeline
from backend.rag.vector_store import get_points_count
from backend.core.config import settings

router = APIRouter(prefix="/rag", tags=["RAG"])

@router.get("/status")
async def get_rag_status():
    """
    Monitoring endpoint checking RAG configuration and active index statistics.
    """
    points = get_points_count()
    return {
        "status": "healthy",
        "collection": settings.QDRANT_COLLECTION,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_size": 384,
        "points": points
    }

@router.post("/retrieve", response_model=RetrievalResponse)
async def retrieve_rag_evidence(request: RetrievalRequest):
    """
    Retrieves Top-K semantically matching context evidence chunks for a query,
    enforcing isolation constraints for search sessions.
    """
    try:
        results = await run_retrieval_pipeline(
            query=request.query,
            search_id=request.search_id,
            top_k=request.top_k
        )
        return RetrievalResponse(
            query=request.query,
            search_id=request.search_id,
            total=len(results),
            results=results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic evidence retrieval failed: {str(e)}"
        )
