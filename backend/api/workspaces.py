from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, delete

from backend.database.postgres import AsyncSessionLocal
from backend.database.models import Workspace, WorkspaceResearch, ResearchSessionModel, GeneratedAnswerModel, CrawlResult
from backend.rag.pipeline import run_retrieval_pipeline
from backend.llm.gemini import GeminiProvider
from backend.llm.context_builder import build_grounding_context
from backend.llm.prompts import SYSTEM_INSTRUCTION

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

class WorkspaceCreate(BaseModel):
    name: str = Field(..., max_length=200, description="Workspace folder name")
    description: Optional[str] = Field(default=None, description="Optional description")

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

class WorkspaceDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    projects: List[Dict[str, Any]]

class WorkspaceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(body: WorkspaceCreate):
    """
    Creates a new research workspace category folder.
    """
    async with AsyncSessionLocal() as session:
        try:
            db_ws = Workspace(
                name=body.name,
                description=body.description,
                created_at=datetime.utcnow()
            )
            session.add(db_ws)
            await session.commit()
            await session.refresh(db_ws)
            return db_ws
        except Exception as e:
            print(f"Workspace creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workspace."
            )

@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces():
    """
    Returns a list of saved workspaces.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Workspace).order_by(Workspace.created_at.desc())
            res = await session.execute(stmt)
            return res.scalars().all()
        except Exception as e:
            print(f"Listing workspaces failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list workspaces."
            )

@router.get("/{id}", response_model=WorkspaceDetailResponse)
async def get_workspace_details(id: int):
    """
    Retrieves workspace name and list of added research sessions.
    """
    async with AsyncSessionLocal() as session:
        ws = await session.get(Workspace, id)
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {id} not found."
            )
            
        # Get linked research projects
        stmt = select(ResearchSessionModel).join(
            WorkspaceResearch, WorkspaceResearch.research_id == ResearchSessionModel.id
        ).where(WorkspaceResearch.workspace_id == id)
        
        res = await session.execute(stmt)
        projects = res.scalars().all()
        
        return WorkspaceDetailResponse(
            id=ws.id,
            name=ws.name,
            description=ws.description,
            created_at=ws.created_at,
            projects=[
                {
                    "research_id": p.id,
                    "query": p.query,
                    "status": p.status,
                    "coverage_score": p.coverage_score,
                    "started_at": p.started_at
                }
                for p in projects
            ]
        )

@router.post("/{id}/research/{research_id}", status_code=status.HTTP_200_OK)
async def link_research_to_workspace(id: int, research_id: int):
    """
    Links a research project session to a workspace.
    """
    async with AsyncSessionLocal() as session:
        # Check workspace and session exist
        ws = await session.get(Workspace, id)
        if not ws:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workspace {id} not found."
            )
            
        rs = await session.get(ResearchSessionModel, research_id)
        if not rs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {research_id} not found."
            )
            
        # Verify not already linked
        stmt = select(WorkspaceResearch).where(
            WorkspaceResearch.workspace_id == id,
            WorkspaceResearch.research_id == research_id
        )
        existing = await session.execute(stmt)
        if existing.scalars().first():
            return {"status": "already_linked"}
            
        try:
            link = WorkspaceResearch(
                workspace_id=id,
                research_id=research_id,
                added_at=datetime.utcnow()
            )
            session.add(link)
            await session.commit()
            return {"status": "success", "workspace_id": id, "research_id": research_id}
        except Exception as e:
            print(f"Failed to link research to workspace: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to link research session."
            )

@router.delete("/{id}/research/{research_id}")
async def unlink_research_from_workspace(id: int, research_id: int):
    """
    Removes a research session from a workspace.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = delete(WorkspaceResearch).where(
                WorkspaceResearch.workspace_id == id,
                WorkspaceResearch.research_id == research_id
            )
            await session.execute(stmt)
            await session.commit()
            return {"status": "success", "workspace_id": id, "research_id": research_id}
        except Exception as e:
            print(f"Failed to unlink research from workspace: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove research session."
            )

@router.post("/{id}/search")
async def search_workspace_evidence(id: int, body: WorkspaceSearchRequest):
    """
    Semantic search over Qdrant evidence associated with research inside the workspace.
    Does NOT query the live web.
    """
    async with AsyncSessionLocal() as session:
        # Load linked research IDs
        stmt = select(WorkspaceResearch.research_id).where(WorkspaceResearch.workspace_id == id)
        res = await session.execute(stmt)
        linked_ids = [row[0] for row in res.fetchall()]
        
        if not linked_ids:
            return {
                "answer": "No research sessions have been linked to this workspace folder yet. Please add projects to query their evidence.",
                "citations": [],
                "evidences": [],
                "sources": []
            }
            
        # We query evidence matching any of the linked research session IDs.
        # Run semantic retrieval against Qdrant.
        # Since retrieve_evidence in vector_store handles filtering on search_id,
        # we can query chunks for each search_id and combine them, sorting by score!
        from backend.rag.vector_store import search_similar
        from backend.rag.embeddings import embed_texts
        
        query_vector = embed_texts([body.query])[0]
        
        combined_chunks = []
        for r_id in linked_ids:
            chunks = search_similar(query_vector, search_id=r_id, top_k=5)
            combined_chunks.extend(chunks)
            
        # Sort combined chunks by similarity score
        combined_chunks.sort(key=lambda c: c.score, reverse=True)
        top_chunks = combined_chunks[:8]
        
        if not top_chunks:
            return {
                "answer": "No relevant evidence segments matching your workspace search query were found in the folder projects.",
                "citations": [],
                "evidences": [],
                "sources": []
            }
            
        # Build grounding context
        context_str, citations = build_grounding_context(top_chunks)
        
        # Call Gemini generator
        provider = GeminiProvider()
        prompt = f"Workspace query: {body.query}\n\nWorkspace Evidence Context:\n{context_str}"
        answer_text = await provider.generate(SYSTEM_INSTRUCTION, prompt)
        
        # Map source IDs
        # Fetch crawl results for the linked projects to reconstruct source domains
        crawl_stmt = select(CrawlResult).where(CrawlResult.search_id.in_(linked_ids)).order_by(CrawlResult.id)
        crawl_res = await session.execute(crawl_stmt)
        pages = crawl_res.scalars().all()
        
        url_to_source_id = {p.url: f"src_{idx + 1}" for idx, p in enumerate(pages)}
        
        frontend_citations = []
        frontend_evidences = []
        for c in citations:
            evidence_id = f"ev_{c.id}"
            source_id = url_to_source_id.get(c.url, "src_1")
            
            # Read snippet text
            ev_item = next((ch for ch in top_chunks if ch.id == c.chunk_id), None)
            text_content = ev_item.text if ev_item else ""
            score_pct = int((ev_item.score if ev_item else 0.85) * 100)
            
            frontend_evidences.append({
                "id": evidence_id,
                "sourceId": source_id,
                "content": text_content,
                "relevanceScore": score_pct
            })
            frontend_citations.append({
                "id": c.id,
                "sourceId": source_id,
                "evidenceId": evidence_id
            })

        sources_list = []
        for idx, p in enumerate(pages):
            sources_list.append({
                "id": f"src_{idx + 1}",
                "title": p.title or "Discovered Source",
                "url": p.url,
                "domain": p.url.split("//")[-1].split("/")[0]
            })
            
        return {
            "answer": answer_text,
            "citations": frontend_citations,
            "evidences": frontend_evidences,
            "sources": sources_list
        }
