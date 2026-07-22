import asyncio
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json

from backend.core.config import settings
from backend.core.rate_limit import check_rate_limit
from backend.observability import start_metrics_tracking, track_stage_duration
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import ResearchConversation, ResearchMessage
from backend.intelligence.followup import EvidenceFirstFollowUp

router = APIRouter(prefix="/research", tags=["follow-up"])

class FollowUpRequest(BaseModel):
    query: str = Field(..., max_length=4000, description="The follow-up query text")
    conversation_id: Optional[int] = Field(default=None, description="Active chat conversation identifier")

class CitationModel(BaseModel):
    id: int
    sourceId: str
    evidenceId: str

class EvidenceModel(BaseModel):
    id: str
    sourceId: str
    content: str
    relevanceScore: int

class SourceModel(BaseModel):
    id: str
    title: str
    url: str
    domain: str

class FollowUpResponse(BaseModel):
    research_id: int
    used_existing_evidence: bool
    performed_web_search: bool
    answer: str
    citations: List[CitationModel]
    evidences: List[EvidenceModel]
    sources: List[SourceModel]

def make_sse_event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"

@router.post("/{research_id}/follow-up", response_model=FollowUpResponse, dependencies=[Depends(check_rate_limit)])
async def post_followup_message(research_id: int, request_body: FollowUpRequest, request: Request):
    """
    Submits a follow-up query using existing research session assets.
    """
    request_id = getattr(request.state, "request_id", "req_none")
    metrics_tracker = start_metrics_tracking(request_body.query, request_id)
    
    # Auto-initialize research conversation if none provided
    conversation_id = request_body.conversation_id
    if not conversation_id:
        async with AsyncSessionLocal() as session:
            try:
                db_conv = ResearchConversation(
                    research_id=research_id
                )
                session.add(db_conv)
                await session.commit()
                await session.refresh(db_conv)
                conversation_id = db_conv.id
            except Exception as e:
                print(f"Failed to create conversation: {e}")
                conversation_id = int(research_id)
                
    try:
        followup_runner = EvidenceFirstFollowUp()
        with track_stage_duration("total_ms"):
            result = await followup_runner.execute_followup(
                research_id=research_id,
                query=request_body.query,
                conversation_id=conversation_id
            )
            
        # Log followup telemetry counts to request_metrics
        # In a real system, we track followup duration
        return FollowUpResponse(
            research_id=result["research_id"],
            used_existing_evidence=result["used_existing_evidence"],
            performed_web_search=result["performed_web_search"],
            answer=result["answer"],
            citations=result["citations"],
            evidences=result["evidences"],
            sources=result["sources"]
        )
    except Exception as e:
        print(f"Follow-up query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Follow-up answer synthesis failed: {str(e)}"
        )

@router.post("/{research_id}/follow-up/stream", dependencies=[Depends(check_rate_limit)])
async def post_followup_message_stream(research_id: int, request_body: FollowUpRequest, request: Request):
    """
    Streams a follow-up answer using SSE.
    """
    # Simply run execution and yield events
    async def sse_generator():
        yield make_sse_event("status", {"stage": "evaluating", "message": "Analyzing follow-up sufficiency..."})
        await asyncio.sleep(0.5)
        
        try:
            followup_runner = EvidenceFirstFollowUp()
            result = await followup_runner.execute_followup(
                research_id=research_id,
                query=request_body.query,
                conversation_id=request_body.conversation_id
            )
            
            # Stream response in fragments
            answer = result["answer"]
            words = answer.split(" ")
            
            # Stream tokens
            for i in range(0, len(words), 3):
                chunk_words = words[i:i+3]
                token_text = " ".join(chunk_words) + " "
                yield make_sse_event("token", {"text": token_text})
                await asyncio.sleep(0.05)
                
            # Stream done payload
            yield make_sse_event("done", result)
            
        except Exception as e:
            yield make_sse_event("error", {"message": f"Follow-up stream failed: {str(e)}"})
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")
