import time
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from backend.core.config import settings
from backend.database.postgres import AsyncSessionLocal
from backend.database.models import ResearchSessionModel, GeneratedAnswerModel, CrawlResult, ResearchConversation, ResearchMessage, MessageEvidence
from backend.rag.pipeline import run_retrieval_pipeline, run_indexing_pipeline
from backend.llm.provider import LLMProvider
from backend.llm.gemini import GeminiProvider
from backend.llm.answer_generator import generate_grounded_answer
from backend.llm.models import GroundingEvidence
from backend.intelligence.research_loop import AutonomousResearchLoop, domain_in_url

class EvidenceFirstFollowUp:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or GeminiProvider()
        self.research_loop = AutonomousResearchLoop(self.provider)

    async def execute_followup(
        self,
        research_id: int,
        query: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes follow-up conversation queries reusing existing evidence.
        Only triggers SearXNG web searches if current Qdrant evidence is insufficient.
        """
        start_time = time.time()
        
        # 1. Verify session exists
        async with AsyncSessionLocal() as session:
            sess_db = await session.get(ResearchSessionModel, research_id)
            if not sess_db:
                raise ValueError(f"Research session {research_id} not found.")
            search_id = sess_db.id

        # 2. Query Qdrant with follow-up query filtered by search_id
        top_k = 8
        retrieved_chunks = await run_retrieval_pipeline(query, search_id, top_k=top_k)
        
        # Step 1 Check: Minimum similarity threshold
        highest_score = max([c.score for c in retrieved_chunks]) if retrieved_chunks else 0.0
        
        is_sufficient = False
        used_existing_evidence = False
        performed_web_search = False
        
        # Default empty checklist topics for follow-up synthesis
        contradictions = []
        
        if highest_score >= settings.FOLLOWUP_MIN_SIMILARITY:
            # Step 2 Check: Ask Gemini if the passages actually answer the question
            evidence_text = "\n\n".join([f"Snippet [{idx+1}]: {c.text}" for idx, c in enumerate(retrieved_chunks)])
            sys_prompt = (
                "You are an evidence sufficiency validator. Check if the provided snippets "
                "are sufficient to answer the user follow-up question fully and accurately. "
                "Respond with EXACTLY 'YES' if the snippets are sufficient, or 'NO' if they are "
                "insufficient or missing details."
            )
            prompt = f"Follow-up Question: {query}\n\nEvidence Snippets:\n{evidence_text}"
            
            try:
                eval_res = await self.provider.generate(sys_prompt, prompt)
                eval_clean = eval_res.strip().upper()
                if eval_clean.startswith("YES"):
                    is_sufficient = True
                    used_existing_evidence = True
            except Exception as e:
                print(f"Sufficiency evaluation model call failed: {e}")
                is_sufficient = False

        # 3. Handle sufficiency result branches
        final_chunks = retrieved_chunks
        
        if is_sufficient:
            # Branch A: Sufficient! Synthesize answer directly from existing RAG
            print(f"Evidence sufficient (Similarity score: {highest_score:.2f}). Answering from Qdrant cache...")
        else:
            # Branch B: Insufficient! Trigger targeted subquery searches
            print(f"Evidence insufficient (Similarity score: {highest_score:.2f}). Triggering targeted live search...")
            performed_web_search = True
            used_existing_evidence = True # Combined old + new
            
            # Decompose follow-up question into 1-2 targeted queries
            sys_decomposer = (
                "You are a search query decomposer. Break down the follow-up question into "
                "exactly 1 or 2 targeted, search-engine-ready keywords queries to fetch the missing details."
            )
            prompt_decomposer = f"Follow-up Question: {query}"
            subqueries_text = await self.provider.generate(sys_decomposer, prompt_decomposer)
            
            # Extract query list
            subqueries = [line.strip("- *123. ") for line in subqueries_text.split("\n") if line.strip()]
            subqueries = [q for q in subqueries if q][:2] # Cap at 2 queries max
            
            # Execute SearXNG and crawl new resources
            for subq in subqueries:
                try:
                    await self.research_loop.execute_research(subq, max_iterations=1, max_subqueries=1, max_sources=3)
                except Exception as e:
                    print(f"Targeted research loop fallback search failed: {e}")
                    
            # Re-retrieve full set of evidence chunks including newly scraped contexts
            final_chunks = await run_retrieval_pipeline(query, search_id, top_k=10)

        # 4. Generate Grounded Final Response
        # Map Qdrant RetrievedChunks to GroundingEvidence
        grounding_evidences = []
        for c in final_chunks:
            grounding_evidences.append(GroundingEvidence(
                id=c.id,
                url=c.url,
                title=c.title,
                text=c.text,
                chunk_index=c.chunk_index
            ))
            
        # Re-verify and synthesize grounded answer
        from backend.llm.context_builder import build_grounding_context
        from backend.llm.prompts import SYSTEM_INSTRUCTION
        
        context_str, final_citations = build_grounding_context(final_chunks)
        prompt_synthesizer = f"Question: {query}\n\nEvidence Context:\n{context_str}"
        
        answer_text = await self.provider.generate(SYSTEM_INSTRUCTION, prompt_synthesizer)
        
        # 5. Reconstruct response details for return
        # Fetch crawled pages to build frontend source references
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            stmt = select(CrawlResult).where(CrawlResult.search_id == search_id).order_by(CrawlResult.id)
            result = await session.execute(stmt)
            pages = result.scalars().all()
            
        url_to_source_id = {p.url: f"src_{idx + 1}" for idx, p in enumerate(pages)}
        
        frontend_citations = []
        frontend_evidences = []
        for c in final_citations:
            evidence_id = f"ev_{c.id}"
            source_id = url_to_source_id.get(c.url, "src_1")
            
            # Read snippet text
            ev_item = next((ch for ch in final_chunks if ch.id == c.chunk_id), None)
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

        # Save conversation messages to database if conversation_id is provided
        if conversation_id:
            async with AsyncSessionLocal() as session:
                try:
                    # Save User message
                    user_msg = ResearchMessage(
                        conversation_id=conversation_id,
                        role="user",
                        content=query,
                        created_at=datetime.utcnow()
                    )
                    session.add(user_msg)
                    await session.commit()
                    await session.refresh(user_msg)
                    
                    # Save Assistant message
                    assistant_msg = ResearchMessage(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer_text,
                        created_at=datetime.utcnow()
                    )
                    session.add(assistant_msg)
                    await session.commit()
                    await session.refresh(assistant_msg)
                    
                    # Save used message evidence links
                    for ev in frontend_evidences:
                        msg_ev = MessageEvidence(
                            message_id=assistant_msg.id,
                            chunk_id=ev["id"],
                            citation_id=int(ev["id"].split("_")[-1]) if "_" in ev["id"] else 1
                        )
                        session.add(msg_ev)
                    await session.commit()
                except Exception as db_err:
                    print(f"Failed to log follow-up messages in database: {db_err}")

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "research_id": research_id,
            "used_existing_evidence": used_existing_evidence,
            "performed_web_search": performed_web_search,
            "answer": answer_text,
            "citations": frontend_citations,
            "evidences": frontend_evidences,
            "sources": sources_list,
            "duration_ms": duration_ms
        }
