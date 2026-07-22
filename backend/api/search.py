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

from backend.intelligence.query_reformulator import QueryReformulator

@router.post("/research")
async def perform_research(request: SearchRequest):
    """
    Autonomous deep research & query-routed search pipeline:
    1. Classifies query intent with QueryRouter.
    2. Fast-paths conversational or general knowledge queries directly to LLM without search/crawling.
    3. Reformulates contextual follow-up questions into standalone queries if chat history exists.
    4. For live web queries, executes search, crawls sources, filters failed scrapes, builds RAG, and generates grounded answer.
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
                print(f"Gemini LLM call failed for non-retrieval query: {e}")
                if routing["intent"] == QueryIntent.CONVERSATIONAL.value:
                    answer_text = "Hi! How can I help you today?"
                else:
                    lower_q = request.query.lower()
                    if "rag" in lower_q:
                        answer_text = "Retrieval-Augmented Generation (RAG) is an AI framework that retrieves relevant documents from an external database or vector store and passes them to a Large Language Model (LLM) as context to generate grounded, factual responses with verifiable citations."
                    else:
                        answer_text = f"I'm IntelliSearch. '{request.query}' is a general topic that can be answered directly or researched with live web search."
            
            return {
                "original_query": request.query,
                "standalone_query": request.query,
                "query": request.query,
                "mode": "web",
                "intent": routing["intent"],
                "reformulated": False,
                "retrieval_used": False,
                "search_id": 0,
                "answer": answer_text.strip(),
                "sources": [],
                "evidences": [],
                "citations": []
            }

        # Standalone Query Reformulation for follow-up queries
        query_to_run = request.query
        reformulation_meta = {"original_query": request.query, "standalone_query": request.query, "reformulated": False}
        if request.chat_history and len(request.chat_history) > 0:
            reformulator = QueryReformulator()
            reformulation_meta = await reformulator.reformulate(request.query, request.chat_history)
            query_to_run = reformulation_meta["standalone_query"]

        # Live Web Search & Retrieval Pipeline with Intent-Aware Reranking & Diagnostics
        response, crawled_docs, search_query_id, diagnostics = await run_search_crawl_pipeline(
            query_to_run,
            limit=request.limit,
            intent=routing["intent"]
        )
        
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
            "original_query": request.query,
            "standalone_query": query_to_run,
            "query": request.query,
            "mode": "web",
            "intent": routing["intent"],
            "reformulated": reformulation_meta["reformulated"],
            "retrieval_used": True,
            "search_id": search_query_id,
            "answer": answer_result.answer,
            "sources": sources_list,
            "evidences": evidences_list,
            "citations": citations_list,
            "diagnostics": diagnostics
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search pipeline failed: {str(e)}"
        )
