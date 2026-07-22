from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select

from backend.database.postgres import AsyncSessionLocal
from backend.database.models import ResearchSessionModel, ResearchNote, SavedSource

router = APIRouter(prefix="/research", tags=["saved"])

class NoteCreate(BaseModel):
    content: str = Field(..., description="Note text content")

class BookmarkCreate(BaseModel):
    url: str = Field(..., description="Webpage link to bookmark")
    title: Optional[str] = Field(default=None, description="Optional title")

@router.post("/{id}/save")
async def save_research_session(id: int):
    """
    Saves a completed research session by flagging its status.
    """
    async with AsyncSessionLocal() as session:
        rs = await session.get(ResearchSessionModel, id)
        if not rs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {id} not found."
            )
            
        try:
            rs.status = "saved"
            await session.commit()
            return {"status": "success", "research_id": id, "saved": True}
        except Exception as e:
            print(f"Failed to save research session: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save research project."
            )

@router.get("/saved")
async def get_saved_research_sessions():
    """
    Returns all saved research sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(ResearchSessionModel).where(ResearchSessionModel.status == "saved").order_by(ResearchSessionModel.started_at.desc())
            res = await session.execute(stmt)
            sessions = res.scalars().all()
            
            return [
                {
                    "research_id": s.id,
                    "query": s.query,
                    "status": s.status,
                    "iterations": s.iterations,
                    "coverage_score": s.coverage_score,
                    "sources_analyzed": s.sources_analyzed,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at
                }
                for s in sessions
            ]
        except Exception as e:
            print(f"Failed to list saved research: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch saved research sessions."
            )

@router.post("/{id}/note")
async def add_research_note(id: int, body: NoteCreate):
    """
    Attaches or updates a note text on a research session.
    """
    async with AsyncSessionLocal() as session:
        rs = await session.get(ResearchSessionModel, id)
        if not rs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {id} not found."
            )
            
        try:
            # Check if note exists
            stmt = select(ResearchNote).where(ResearchNote.research_id == id)
            res = await session.execute(stmt)
            note = res.scalars().first()
            
            if note:
                note.content = body.content
                note.updated_at = datetime.utcnow()
            else:
                note = ResearchNote(
                    research_id=id,
                    content=body.content,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(note)
                
            await session.commit()
            return {"status": "success", "note_id": note.id, "content": note.content}
        except Exception as e:
            print(f"Failed to save note: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add research note."
            )

@router.get("/{id}/note")
async def get_research_note(id: int):
    """
    Retrieves note attached to research session.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ResearchNote).where(ResearchNote.research_id == id)
        res = await session.execute(stmt)
        note = res.scalars().first()
        if not note:
            return {"content": ""}
        return {"content": note.content}

@router.post("/{id}/bookmark")
async def bookmark_source_link(id: int, body: BookmarkCreate):
    """
    Bookmarks individual crawled webpage source links inside research sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(SavedSource).where(SavedSource.research_id == id, SavedSource.url == body.url)
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return {"status": "already_bookmarked", "bookmark_id": existing.id}
                
            bookmark = SavedSource(
                research_id=id,
                url=body.url,
                title=body.title or "Bookmarked webpage",
                created_at=datetime.utcnow()
            )
            session.add(bookmark)
            await session.commit()
            return {"status": "success", "bookmark_id": bookmark.id, "url": bookmark.url}
        except Exception as e:
            print(f"Failed to bookmark link: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bookmark source."
            )

@router.get("/{id}/bookmarks")
async def list_session_bookmarks(id: int):
    """
    Returns bookmarks for a specific session.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(SavedSource).where(SavedSource.research_id == id)
            res = await session.execute(stmt)
            bookmarks = res.scalars().all()
            return [
                {"id": b.id, "url": b.url, "title": b.title, "created_at": b.created_at}
                for b in bookmarks
            ]
        except Exception as e:
            print(f"Listing bookmarks failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve bookmarks."
            )
