from pydantic import BaseModel
from typing import List
import json
from google.genai import types
from backend.llm.gemini import GeminiProvider
from backend.core.config import settings

class PlannerOutput(BaseModel):
    objective: str
    topics: List[str]

class ResearchPlanner:
    """
    Analyzes the user's initial query and decomposes it into high-level objectives and a checklist of topics.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    async def plan(self, query: str) -> PlannerOutput:
        client = self.provider._get_client()
        
        system_instruction = (
            "You are a research planning assistant for an autonomous search engine.\n"
            "Your task is NOT to answer the query, but to construct a structured research plan.\n"
            "Analyze the user query and extract:\n"
            "1. A concise, clear 'objective' for the research session.\n"
            "2. A checklist of 3 to 8 specific 'topics' that must be researched to answer the query comprehensively.\n"
            "Be specific about what must be crawled (e.g. if the user asks for a comparison, include deployment, routing, SEO, etc. as individual topics).\n"
            "Do NOT include placeholders or meta-questions."
        )
        
        prompt = f"User Search Query: {query}"
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=PlannerOutput
            )
            
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            text = response.text or ""
            data = json.loads(text)
            return PlannerOutput(**data)
            
        except Exception as e:
            print(f"Research plan generation failed: {e}. Falling back to default heuristics.")
            # Safety fallback plan
            return PlannerOutput(
                objective=f"Analyze and research: {query}",
                topics=["general background", "detailed comparison", "deployment and routing considerations", "use cases"]
            )
