import json
from typing import List, Dict, Set
from google.genai import types
from pydantic import BaseModel
from backend.intelligence.models import Contradiction, EvidenceItem
from backend.llm.gemini import GeminiProvider
from backend.core.config import settings

class ContradictionOutputItem(BaseModel):
    topic: str
    claim_a: str
    source_a: str # URL
    claim_b: str
    source_b: str # URL
    severity: str = "low" # low, medium, high

class ContradictionOutput(BaseModel):
    contradictions: List[ContradictionOutputItem] = []

class ContradictionDetector:
    """
    Detects fact conflicts and source disagreements across aggregated evidence.
    Groups evidence by planned topics to avoid O(n^2) comparisons.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    async def detect_contradictions(self, topics: List[str], evidence: List[EvidenceItem]) -> List[Contradiction]:
        if len(evidence) < 2:
            return []
            
        client = self.provider._get_client()
        
        # 1. Group high-relevance evidence by plan topics (keyword heuristic)
        topic_evidence: Dict[str, List[EvidenceItem]] = {t: [] for t in topics}
        
        for item in evidence:
            text_lower = item.text.lower()
            for topic in topics:
                # Group if topic words are present in text
                topic_words = [w for w in topic.lower().split() if len(w) > 3]
                if any(w in text_lower for w in topic_words) or topic.lower() in text_lower:
                    topic_evidence[topic].append(item)
                    
        contradictions_found: List[Contradiction] = []
        
        # 2. Inspect topics that have evidence from at least 2 distinct domains
        for topic, items in topic_evidence.items():
            domains = {item.domain for item in items}
            if len(domains) < 2:
                continue
                
            # Keep top 4 items for this topic to fit prompt budget
            items_to_compare = sorted(items, key=lambda x: x.similarity_score, reverse=True)[:4]
            
            system_instruction = (
                "You are an evidence verification assistant.\n"
                "Your job is to identify direct factual disagreements, contradictions, or conflicting claims in the provided source texts regarding the topic.\n"
                "Compare the claims from different sources.\n"
                "If two sources directly contradict (e.g. source A says 'feature is enabled by default' and source B says 'feature must be manually enabled'), describe the conflict in detail.\n"
                "Do NOT try to resolve which source is correct. Simply report the conflict.\n"
                "If there are no direct contradictions, return an empty list.\n"
                "Return JSON matching the schema."
            )
            
            evidence_str = []
            for idx, item in enumerate(items_to_compare):
                evidence_str.append(f"Source [{idx+1}]: {item.url}\nText: {item.text}\n")
                
            prompt = (
                f"Topic: {topic}\n\n"
                f"Evidence to Compare:\n" + "\n".join(evidence_str)
            )
            
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=ContradictionOutput
                )
                
                response = await client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                
                data = json.loads(response.text or "{}")
                output = ContradictionOutput(**data)
                
                for item in output.contradictions:
                    contradictions_found.append(Contradiction(
                        topic=item.topic,
                        claim_a=item.claim_a,
                        source_a=item.source_a,
                        claim_b=item.claim_b,
                        source_b=item.source_b,
                        severity=item.severity
                    ))
                    
            except Exception as e:
                print(f"Contradiction detection failed for topic '{topic}': {e}")
                
        return contradictions_found
