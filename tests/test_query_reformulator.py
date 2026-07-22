import pytest
import asyncio
from backend.intelligence.query_reformulator import QueryReformulator

class MockGeminiProvider:
    async def generate(self, system_prompt: str, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "what about performance?" in prompt_lower:
            return "Compare the performance of React and Next.js"
        elif "which has the better camera?" in prompt_lower:
            return "Compare the camera quality of iPhone 16 and Galaxy S25"
        elif "how does it work?" in prompt_lower:
            return "How does Retrieval-Augmented Generation (RAG) work?"
        elif "what about google?" in prompt_lower:
            return "Latest Google news today"
        elif "what's the weather in chennai?" in prompt_lower:
            # Unrelated query returns identical text
            return "What's the weather in Chennai?"
        return prompt.split("Latest User Query:")[-1].split("\n")[0].strip()

@pytest.mark.asyncio
async def test_followup_reformulation_react_nextjs():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Compare React and Next.js"},
        {"role": "assistant", "content": "React is a UI library whereas Next.js is a fullstack React framework with SSR."}
    ]
    result = await reformulator.reformulate("What about performance?", history)
    assert result["reformulated"] is True
    assert result["original_query"] == "What about performance?"
    assert result["standalone_query"] == "Compare the performance of React and Next.js"

@pytest.mark.asyncio
async def test_followup_reformulation_iphone_galaxy():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Compare iPhone 16 and Galaxy S25"},
        {"role": "assistant", "content": "Both are flagship smartphones with top cameras and processors."}
    ]
    result = await reformulator.reformulate("Which has the better camera?", history)
    assert result["reformulated"] is True
    assert result["standalone_query"] == "Compare the camera quality of iPhone 16 and Galaxy S25"

@pytest.mark.asyncio
async def test_followup_reformulation_explain_rag():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Explain RAG"},
        {"role": "assistant", "content": "RAG stands for Retrieval-Augmented Generation."}
    ]
    result = await reformulator.reformulate("How does it work?", history)
    assert result["reformulated"] is True
    assert result["standalone_query"] == "How does Retrieval-Augmented Generation (RAG) work?"

@pytest.mark.asyncio
async def test_followup_openai_to_google():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Latest OpenAI news"},
        {"role": "assistant", "content": "OpenAI announced new model updates."}
    ]
    result = await reformulator.reformulate("What about Google?", history)
    assert result["reformulated"] is True
    assert result["standalone_query"] == "Latest Google news today"

@pytest.mark.asyncio
async def test_conversational_greeting_bypasses_reformulation():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Explain Python"},
        {"role": "assistant", "content": "Python is a high-level programming language."}
    ]
    result = await reformulator.reformulate("Thanks", history)
    assert result["reformulated"] is False
    assert result["standalone_query"] == "Thanks"

@pytest.mark.asyncio
async def test_unrelated_topic_switch_not_rewritten():
    reformulator = QueryReformulator(provider=MockGeminiProvider())
    history = [
        {"role": "user", "content": "Latest AI news"},
        {"role": "assistant", "content": "AI advancements in LLMs continue."}
    ]
    result = await reformulator.reformulate("What's the weather in Chennai?", history)
    assert result["reformulated"] is False
    assert result["standalone_query"] == "What's the weather in Chennai?"

if __name__ == "__main__":
    asyncio.run(test_followup_reformulation_react_nextjs())
    asyncio.run(test_followup_reformulation_iphone_galaxy())
    asyncio.run(test_followup_reformulation_explain_rag())
    asyncio.run(test_followup_openai_to_google())
    asyncio.run(test_conversational_greeting_bypasses_reformulation())
    asyncio.run(test_unrelated_topic_switch_not_rewritten())
    print("All QueryReformulator test assertions passed successfully!")
