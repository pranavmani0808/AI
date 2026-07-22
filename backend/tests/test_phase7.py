import pytest
import httpx
from sqlalchemy import select
from datetime import datetime

from backend.main import app
from backend.core.config import settings
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import ResearchSessionModel, Workspace, WorkspaceResearch, ResearchNote, SavedSource
from backend.intelligence.research_loop import domain_in_url

def test_domain_in_url_filtering():
    """Verify whitelist/blacklist domain extraction check matching utility."""
    assert domain_in_url("https://react.dev/reference/react", "react.dev") is True
    assert domain_in_url("https://beta.react.dev/reference/react", "react.dev") is True
    assert domain_in_url("https://nextjs.org/docs", "react.dev") is False
    assert domain_in_url("https://google.com/search", "google.com") is True

@pytest.mark.asyncio
async def test_phase7_all_operations():
    """Run all Phase 7 tests sequentially in a single event loop to preserve DB connection pool."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with AsyncSessionLocal() as db_session:
            # 1. TEST WORKSPACE CRUD
            ws = Workspace(name="Final Year Project", description="Test Workspace", created_at=datetime.utcnow())
            db_session.add(ws)
            await db_session.commit()
            await db_session.refresh(ws)
            
            ws_id = ws.id
            
            # Verify listing endpoint
            response = await client.get("/api/workspaces")
            assert response.status_code == 200
            data = response.json()
            assert any(w["id"] == ws_id for w in data)
            
            # Create research session
            rs = ResearchSessionModel(
                query="Deep RAG research",
                status="completed",
                iterations=1,
                coverage_score=0.85,
                sources_analyzed=3,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db_session.add(rs)
            await db_session.commit()
            await db_session.refresh(rs)
            
            rs_id = rs.id
            
            # Link research session to workspace
            link_res = await client.post(f"/api/workspaces/{ws_id}/research/{rs_id}")
            assert link_res.status_code == 200
            
            # Try duplicate link - should return status "already_linked"
            duplicate_res = await client.post(f"/api/workspaces/{ws_id}/research/{rs_id}")
            assert duplicate_res.status_code == 200
            assert duplicate_res.json()["status"] == "already_linked"

            # 2. TEST SAVED RESEARCH & ANNOTATIONS
            save_res = await client.post(f"/api/research/{rs_id}/save")
            assert save_res.status_code == 200
            
            # Add note
            note_res = await client.post(f"/api/research/{rs_id}/note", json={"content": "React is standard clientside library"})
            assert note_res.status_code == 200
            
            # Verify note
            get_note = await client.get(f"/api/research/{rs_id}/note")
            assert get_note.status_code == 200
            assert "React is standard" in get_note.json()["content"]
            
            # Bookmark link
            bookmark_res = await client.post(f"/api/research/{rs_id}/bookmark", json={"url": "https://react.dev", "title": "React documentation"})
            assert bookmark_res.status_code == 200

            # 3. TEST EXPORTS ENDPOINTS
            # Test markdown export
            md_res = await client.get(f"/api/research/{rs_id}/export?format=markdown")
            assert md_res.status_code == 200
            assert "text/markdown" in md_res.headers["content-type"]
            
            # Test PDF export
            pdf_res = await client.get(f"/api/research/{rs_id}/export?format=pdf")
            assert pdf_res.status_code == 200
            assert "application/pdf" in pdf_res.headers["content-type"]
            
            # Test DOCX export
            docx_res = await client.get(f"/api/research/{rs_id}/export?format=docx")
            assert docx_res.status_code == 200
            assert "application/vnd.openxmlformats" in docx_res.headers["content-type"]
            
            # Clean up database test records
            await db_session.delete(rs)
            await db_session.delete(ws)
            await db_session.commit()
