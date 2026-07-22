import pytest
import asyncio
from backend.intelligence.query_router import QueryRouter, QueryIntent

@pytest.mark.asyncio
async def test_conversational_queries():
    router = QueryRouter()
    conversational_samples = [
        "hi", "hello", "hey", "good morning", "thanks", "thank you",
        "how are you?", "who are you?", "what can you do?"
    ]
    for query in conversational_samples:
        result = await router.route_query(query, selected_mode="web")
        assert result["intent"] == QueryIntent.CONVERSATIONAL.value
        assert result["retrieval_used"] is False

@pytest.mark.asyncio
async def test_general_knowledge_queries():
    router = QueryRouter()
    general_samples = [
        "What is Python?",
        "Explain recursion",
        "What is an API?"
    ]
    for query in general_samples:
        result = await router.route_query(query, selected_mode="web")
        assert result["intent"] in (QueryIntent.GENERAL_KNOWLEDGE.value, QueryIntent.CONVERSATIONAL.value)
        assert result["retrieval_used"] is False

@pytest.mark.asyncio
async def test_live_web_search_queries():
    router = QueryRouter()
    web_samples = [
        "latest AI news today",
        "current iPhone price in India",
        "latest Next.js release 2026"
    ]
    for query in web_samples:
        result = await router.route_query(query, selected_mode="web")
        assert result["intent"] in (QueryIntent.WEB_SEARCH.value, QueryIntent.PRODUCT.value)
        assert result["retrieval_used"] is True

@pytest.mark.asyncio
async def test_research_queries():
    router = QueryRouter()
    result = await router.route_query("Compare React and Next.js in depth", selected_mode="research")
    assert result["intent"] == QueryIntent.RESEARCH.value
    assert result["retrieval_used"] is True

if __name__ == "__main__":
    asyncio.run(test_conversational_queries())
    asyncio.run(test_general_knowledge_queries())
    asyncio.run(test_live_web_search_queries())
    asyncio.run(test_research_queries())
    print("All QueryRouter tests passed successfully!")
