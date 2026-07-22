import json
from typing import List
from google.genai import types
from pydantic import BaseModel
from backend.intelligence.models import CoverageReport, EvidenceItem
from backend.llm.gemini import GeminiProvider
from backend.core.config import settings

class CoverageReportOutput(BaseModel):
    covered_topics: List[str]
    missing_topics: List[str]

class CoverageAnalyzer:
    """
    Evaluates the semantic coverage of retrieved evidence against the planned topics list.
    Identifies remaining search gaps to target.
    """
    def __init__(self, provider: GeminiProvider = None):
        self.provider = provider or GeminiProvider()

    async def analyze_coverage(self, topics: List[str], evidence: List[EvidenceItem]) -> CoverageReport:
        if not topics:
            return CoverageReport(covered_topics=[], missing_topics=[], coverage_score=1.0, needs_more_research=False)
            
        if not evidence:
            return CoverageReport(covered_topics=[], missing_topics=topics.copy(), coverage_score=0.0, needs_more_research=True)
            
        client = self.provider._get_client()
        
        system_instruction = (
            "You are a research evaluation assistant.\n"
            "Analyze the retrieved evidence text snippets and match them against the checklist of planned topics.\n"
            "For each topic, decide whether the evidence contains sufficient information to confidently address it.\n"
            "If a topic has no supporting evidence or only generic references with no specific details, classify it as 'missing_topic'.\n"
            "Return the list of 'covered_topics' and 'missing_topics' as JSON matching the schema.\n"
            "Every topic from the checklist must be placed into exactly one of the two lists."
        )
        
        # Build context string of evidence snippets for LLM analysis
        evidence_snippets = []
        for idx, item in enumerate(evidence[:12]): # Cap at 12 top evidence items to fit LLM instructions
            evidence_snippets.append(f"Evidence [{idx+1}]:\nSource: {item.url}\nText: {item.text}\n")
            
        prompt = (
            f"Planned Topics Checklist: {', '.join(topics)}\n\n"
            f"Retrieved Evidence:\n" + "\n".join(evidence_snippets)
        )
        
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=CoverageReportOutput
            )
            
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            data = json.loads(response.text or "{}")
            output = CoverageReportOutput(**data)
            
            # Re-verify all planned topics are covered in either list to guard against model hallucination
            covered = [t for t in output.covered_topics if t in topics]
            missing = [t for t in output.missing_topics if t in topics]
            
            # If any topic was omitted, default to missing
            accounted = set(covered).union(set(missing))
            for topic in topics:
                if topic not in accounted:
                    missing.append(topic)
                    
            total_topics = len(topics)
            coverage_score = len(covered) / total_topics if total_topics > 0 else 0.0
            needs_more = coverage_score < settings.RESEARCH_COVERAGE_THRESHOLD
            
            return CoverageReport(
                covered_topics=covered,
                missing_topics=missing,
                coverage_score=round(coverage_score, 2),
                needs_more_research=needs_more
            )
            
        except Exception as e:
            print(f"Coverage analysis failed: {e}. Defaulting to partial coverage.")
            # Default fallback: assume first topic is covered and rest are missing
            return CoverageReport(
                covered_topics=[topics[0]] if topics else [],
                missing_topics=topics[1:] if len(topics) > 1 else topics,
                coverage_score=0.5 if len(topics) > 1 else 0.0,
                needs_more_research=True
            )
