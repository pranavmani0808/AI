import json
from typing import List, Set
from google.genai import types
from pydantic import BaseModel, Field
from backend.intelligence.models import ResearchSubquery
from backend.llm.gemini import GeminiProvider
from backend.core.config import settings

class DecomposerOutputItem(BaseModel):
    query: str
    purpose: str
    priority: str = "medium" # low, medium, high

class DecomposerOutput(BaseModel):
    subqueries: List[DecomposerOutputItem]

class ResearchQueryDecomposer:
    """
    Decomposes research objectives/topics into specific, targeted search engine subqueries.
    Supports initial query decomposition and follow-up gap-filling queries.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    async def decompose(self, original_query: str, objective: str, topics: List[str], existing_queries: Set[str] = None) -> List[ResearchSubquery]:
        """
        Generates the initial set of targeted subqueries.
        """
        client = self.provider._get_client()
        existing = existing_queries or set()
        
        system_instruction = (
            "You are a search query decomposition expert.\n"
            "Given an objective and list of topics to research, generate a list of highly targeted search engine queries.\n"
            "Each query should cover one or two specific topics.\n"
            "Format the query so it is optimal for a web search engine (use keywords, avoid conversational questions).\n"
            f"Generate between 2 and {settings.RESEARCH_MAX_SUBQUERIES} subqueries in total."
        )
        
        prompt = (
            f"Original Query: {original_query}\n"
            f"Research Objective: {objective}\n"
            f"Topics checklist: {', '.join(topics)}\n"
        )
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=DecomposerOutput
            )
            
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            data = json.loads(response.text or "{}")
            items = DecomposerOutput(**data).subqueries
            
            subqueries = []
            subquery_id = len(existing) + 1
            
            for item in items:
                q = item.query.strip().strip('"').strip("'")
                # Deduplicate against already run queries
                if q.lower() in {e.lower() for e in existing}:
                    continue
                subqueries.append(ResearchSubquery(
                    id=subquery_id,
                    query=q,
                    purpose=item.purpose,
                    priority=item.priority,
                    status="pending"
                ))
                existing.add(q.lower())
                subquery_id += 1
                
            # If no unique subqueries were generated, yield a fallback matching the original query
            if not subqueries:
                subqueries.append(ResearchSubquery(
                    id=1,
                    query=original_query,
                    purpose="Fallback query covering entire objective",
                    priority="high",
                    status="pending"
                ))
                
            return subqueries[:settings.RESEARCH_MAX_SUBQUERIES]
            
        except Exception as e:
            print(f"Decomposition failed: {e}. Falling back to default list.")
            # Safety fallback queries
            subqueries = []
            for i, topic in enumerate(topics[:settings.RESEARCH_MAX_SUBQUERIES]):
                subqueries.append(ResearchSubquery(
                    id=i + 1,
                    query=f"{original_query} {topic}",
                    purpose=f"Gather evidence regarding {topic}",
                    priority="high",
                    status="pending"
                ))
            return subqueries

    async def generate_follow_up(self, original_query: str, missing_topics: List[str], existing_queries: Set[str]) -> List[ResearchSubquery]:
        """
        Generates targeted follow-up queries focused exclusively on the missing/gap topics.
        """
        client = self.provider._get_client()
        
        system_instruction = (
            "You are a target query expansion expert.\n"
            "We are researching a user query but identified critical information gaps.\n"
            "Your task is to generate highly targeted search engine queries to fill these specific gaps.\n"
            "Do NOT repeat queries that have already been searched.\n"
            "Keep the queries focused and avoid conversational framing.\n"
            "Generate at most 3 targeted queries."
        )
        
        prompt = (
            f"Original Query: {original_query}\n"
            f"Identified evidence gaps (missing topics): {', '.join(missing_topics)}\n"
            f"Already executed searches (DO NOT REPEAT): {list(existing_queries)}\n"
        )
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=DecomposerOutput
            )
            
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            data = json.loads(response.text or "{}")
            items = DecomposerOutput(**data).subqueries
            
            subqueries = []
            subquery_id = len(existing_queries) + 1
            
            for item in items:
                q = item.query.strip().strip('"').strip("'")
                if q.lower() in {e.lower() for e in existing_queries}:
                    continue
                subqueries.append(ResearchSubquery(
                    id=subquery_id,
                    query=q,
                    purpose=item.purpose,
                    priority=item.priority,
                    status="pending"
                ))
                existing_queries.add(q.lower())
                subquery_id += 1
                
            return subqueries[:3]
            
        except Exception as e:
            print(f"Follow-up query decomposition failed: {e}.")
            # Static fallback for gaps
            subqueries = []
            for i, topic in enumerate(missing_topics[:3]):
                q = f"{original_query} {topic} official documentation"
                if q.lower() not in {e.lower() for e in existing_queries}:
                    subqueries.append(ResearchSubquery(
                        id=len(existing_queries) + 1,
                        query=q,
                        purpose=f"Fallback gap search for {topic}",
                        priority="high",
                        status="pending"
                    ))
                    existing_queries.add(q.lower())
            return subqueries
