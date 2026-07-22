from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from backend.search.models import SearchRequest, SearchResponse
from backend.services.searxng import search_searxng
from backend.search.pipeline import run_search_crawl_pipeline
from backend.rag.pipeline import run_indexing_pipeline, run_retrieval_pipeline
from backend.intelligence.query_router import QueryRouter, QueryIntent
from backend.llm.gemini import GeminiProvider
from backend.llm.prompts import CONVERSATIONAL_SYSTEM_INSTRUCTION, GENERAL_KNOWLEDGE_SYSTEM_INSTRUCTION

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/status")
async def get_search_status():
    return {
        "module": "search",
        "status": "ready",
        "phase": "production"
    }

@router.post("", response_model=SearchResponse)
async def perform_search(request: SearchRequest):
    try:
        results = await search_searxng(request.query, limit=request.limit)
        return SearchResponse(
            query=request.query,
            total=len(results),
            results=results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Web search discovery query failed: {str(e)}"
        )

@router.post("/research")
async def perform_research(request: SearchRequest):
    """
    Autonomous deep research & query-routed search pipeline:
    1. Classifies query intent with QueryRouter.
    2. Fast-paths conversational or general knowledge queries directly to LLM without search/crawling.
    3. For live web queries, executes search, crawls sources, filters failed scrapes, builds RAG, and generates grounded answer.
    """
    try:
        router_engine = QueryRouter()
        routing = await router_engine.route_query(request.query, selected_mode="web")

        # Fast-path for Conversational & General Knowledge without live retrieval
        if not routing["retrieval_used"]:
            provider = GeminiProvider()
            system_prompt = (
                CONVERSATIONAL_SYSTEM_INSTRUCTION 
                if routing["intent"] == QueryIntent.CONVERSATIONAL.value 
                else GENERAL_KNOWLEDGE_SYSTEM_INSTRUCTION
            )
            try:
                answer_text = await provider.generate(system_prompt, f"User Query: {request.query}")
            except Exception as e:
                print(f"Gemini LLM call failed for conversational query: {e}")
                if routing["intent"] == QueryIntent.CONVERSATIONAL.value:
                    answer_text = "Hi! How can I help you today?"
                else:
                    answer_text = "I'm IntelliSearch, your AI research assistant. How can I help you today?"
            
            return {
                "query": request.query,
                "mode": "web",
                "intent": routing["intent"],
                "retrieval_used": False,
                "search_id": 0,
                "answer": answer_text.strip(),
                "sources": [],
                "evidences": [],
                "citations": []
            }

        # Live Web Search & Retrieval Pipeline
        response, crawled_docs, search_query_id = await run_search_crawl_pipeline(request.query, limit=request.limit)
        
        # STEP 6: Filter out failed scrapes before indexing & visual presentation
        valid_crawled_docs = [
            doc for doc in crawled_docs 
            if doc.crawl_status == "SUCCESS" and doc.text and doc.word_count >= 30
        ]

        # 1. Run RAG Indexing Pipeline with valid docs only
        if search_query_id and valid_crawled_docs:
            await run_indexing_pipeline(valid_crawled_docs, search_id=search_query_id)
            
        # 2. Run Retrieval Pipeline
        retrieved_chunks = []
        if search_query_id:
            retrieved_chunks = await run_retrieval_pipeline(request.query, search_id=search_query_id, top_k=6)
            
        # Build output sources mapping valid docs only
        sources_list = []
        url_to_source_id = {}
        for idx, doc in enumerate(valid_crawled_docs):
            source_id = f"src_{idx + 1}"
            domain = doc.url.split("//")[-1].split("/")[0]
            url_to_source_id[doc.url] = source_id
            
            sources_list.append({
                "id": source_id,
                "title": doc.title or f"Source {idx + 1}",
                "url": doc.url,
                "domain": domain,
                "excerpt": doc.description or (doc.text[:200] + "..."),
                "crawledAt": datetime.utcnow().isoformat()
            })
            
        evidences_list = []
        citations_list = []
        for idx, chunk in enumerate(retrieved_chunks):
            evidence_id = f"ev_{idx + 1}"
            source_id = url_to_source_id.get(chunk.url, "src_1")
            
            evidences_list.append({
                "id": evidence_id,
                "sourceId": source_id,
                "content": chunk.text,
                "relevanceScore": int(chunk.score * 100)
            })
            citations_list.append({
                "id": idx + 1,
                "sourceId": source_id,
                "evidenceId": evidence_id
            })
            
        # 3. Generate Grounded Answer
        from backend.llm.answer_generator import generate_grounded_answer
        answer_result = await generate_grounded_answer(
            query=request.query,
            search_id=search_query_id,
            retrieved_chunks=retrieved_chunks
        )
            
        return {
            "query": request.query,
            "mode": "web",
            "intent": routing["intent"],
            "retrieval_used": True,
            "search_id": search_query_id,
            "answer": answer_result.answer,
            "sources": sources_list,
            "evidences": evidences_list,
            "citations": citations_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search pipeline failed: {str(e)}"
        )
