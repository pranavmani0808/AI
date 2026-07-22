import pytest
import asyncio
from typing import List
from backend.llm.provider import LLMProvider
from backend.intelligence.models import ResearchPlan, ResearchSubquery, ResearchSource, EvidenceItem, CoverageReport, Contradiction
from backend.intelligence.planner import ResearchPlanner, PlannerOutput
from backend.intelligence.query_decomposer import ResearchQueryDecomposer
from backend.intelligence.source_scorer import SourceScorer
from backend.intelligence.evidence_manager import EvidenceManager
from backend.intelligence.coverage_analyzer import CoverageAnalyzer
from backend.intelligence.contradiction_detector import ContradictionDetector
from backend.intelligence.synthesis import ResearchSynthesizer
from backend.search.models import SearchResult
from backend.rag.models import RetrievedChunk

class MockIntelligenceLLMProvider(LLMProvider):
    def __init__(self, mode: str = "gap"):
        self.mode = mode

    def _get_client(self):
        class MockGenAIClient:
            def __init__(self, provider):
                self.aio = MockAio(provider)
        class MockAio:
            def __init__(self, provider):
                self.models = MockModels(provider)
        class MockModels:
            def __init__(self, provider):
                self.provider = provider
            async def generate_content(self, model, contents, config=None):
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                text = await self.provider.generate(config.system_instruction, contents)
                return MockResponse(text)
        return MockGenAIClient(self)

    async def generate(self, system_instruction: str, prompt: str) -> str:
        prompt_lower = prompt.lower()
        sys_lower = system_instruction.lower()
        
        # Planner
        if "research planning assistant" in sys_lower:
            return '{"objective": "Compare React and Next.js for production use", "topics": ["routing", "SEO", "performance", "deployment"]}'
            
        # Decomposer (Initial)
        if "search query decomposition" in sys_lower:
            return (
                '{"subqueries": ['
                '  {"query": "React Next.js routing", "purpose": "routing", "priority": "high"},'
                '  {"query": "React Next.js SEO", "purpose": "SEO", "priority": "high"},'
                '  {"query": "React Next.js performance", "purpose": "performance", "priority": "medium"}'
                ']}'
            )
            
        # Decomposer (Follow-up)
        if "target query expansion" in sys_lower:
            return '{"subqueries": [{"query": "React Next.js deployment official documentation", "purpose": "deployment", "priority": "high"}]}'
            
        # Coverage Analyzer
        if "research evaluation assistant" in sys_lower:
            if self.mode == "gap":
                return '{"covered_topics": ["routing", "SEO", "performance"], "missing_topics": ["deployment"]}'
            else:
                return '{"covered_topics": ["routing", "SEO", "performance", "deployment"], "missing_topics": []}'
                
        # Contradiction Detector
        if "evidence verification assistant" in sys_lower:
            return (
                '{"contradictions": ['
                '  {"topic": "routing", "claim_a": "Next.js uses App Router.", "source_a": "https://nextjs.org/docs", "claim_b": "Next.js only supports Pages Router.", "source_b": "https://blog.com", "severity": "medium"}'
                ']}'
            )
            
        # Synthesis
        return "React and Next.js are comparison objects. Next.js supports SSR [1]. React defaults to CSR [2]."

    async def stream(self, system_instruction: str, prompt: str):
        yield "React vs Next.js comparison"

# --- Test Suites ---

@pytest.mark.anyio
async def test_research_planner():
    provider = MockIntelligenceLLMProvider()
    planner = ResearchPlanner(provider)
    result = await planner.plan("Compare React and Next.js")
    
    assert result.objective == "Compare React and Next.js for production use"
    assert "routing" in result.topics
    assert "deployment" in result.topics

@pytest.mark.anyio
async def test_query_decomposer():
    provider = MockIntelligenceLLMProvider()
    decomposer = ResearchQueryDecomposer(provider)
    
    subqueries = await decomposer.decompose(
        original_query="Compare React and Next.js",
        objective="Compare React and Next.js for production use",
        topics=["routing", "SEO", "performance", "deployment"],
        existing_queries=set()
    )
    
    assert len(subqueries) == 3
    assert subqueries[0].query == "React Next.js routing"
    assert subqueries[1].query == "React Next.js SEO"
    
    # Follow-up decomposition
    follow_up = await decomposer.generate_follow_up(
        original_query="Compare React and Next.js",
        missing_topics=["deployment"],
        existing_queries={"react nextjs routing", "react nextjs seo"}
    )
    
    assert len(follow_up) == 1
    assert "deployment" in follow_up[0].query.lower()

def test_source_scorer():
    scorer = SourceScorer()
    
    # Test official Next.js documentation URL
    official = scorer.score_source(
        url="https://nextjs.org/docs/routing",
        title="Routing guide | Next.js",
        excerpt="Next.js supports file-system based routing...",
        query="Next.js routing",
        rank=1
    )
    
    assert official.source_type == "Primary / Official"
    assert official.authority_score > 0.7
    
    # Test standard blog URL
    blog = scorer.score_source(
        url="https://some-tech-blog.com/react-next-js",
        title="Comparison of React and Next.js in 2026",
        excerpt="Let us look at some points comparing these libraries...",
        query="Next.js routing",
        rank=5
    )
    
    assert blog.overall_score < official.overall_score
    # Freshness for 2026 title
    assert blog.freshness_score == 1.0

def test_evidence_manager_deduplication():
    manager = EvidenceManager()
    
    candidates = [
        SearchResult(url="https://nextjs.org/docs", title="Docs", snippet="Docs content", engine="searxng"),
        SearchResult(url="https://nextjs.org/docs", title="Docs Duplicate", snippet="Docs content", engine="searxng"),
        SearchResult(url="https://nextjs.org/docs/routing", title="Routing", snippet="Routing content", engine="searxng"),
        SearchResult(url="https://nextjs.org/docs/seo", title="SEO", snippet="SEO content", engine="searxng"),
        SearchResult(url="https://example.com/blog", title="Blog", snippet="Blog content", engine="searxng")
    ]
    
    crawled = {"https://example.com/blog"}
    domain_counts = {"example.com": 1}
    
    filtered = manager.filter_and_deduplicate(
        candidates=candidates,
        crawled_urls=crawled,
        domain_counts=domain_counts
    )
    
    # "https://example.com/blog" should be skipped (already in crawled)
    # The duplicate "https://nextjs.org/docs" should be skipped
    # Max domain count for nextjs.org is 2. So the 3rd nextjs.org link "/docs/seo" should be skipped!
    assert len(filtered) == 2
    assert filtered[0].url == "https://nextjs.org/docs"
    assert filtered[1].url == "https://nextjs.org/docs/routing"
    assert "https://nextjs.org/docs" in crawled
    assert domain_counts["nextjs.org"] == 2

@pytest.mark.anyio
async def test_coverage_analyzer():
    provider = MockIntelligenceLLMProvider(mode="gap")
    analyzer = CoverageAnalyzer(provider)
    
    evidence = [
        EvidenceItem(
            id="1", search_id=1, subquery_id=1, chunk_id="c1", title="React",
            url="https://react.dev", domain="react.dev", text="React uses components",
            similarity_score=0.8, source_quality_score=0.9
        )
    ]
    
    report = await analyzer.analyze_coverage(
        topics=["routing", "SEO", "performance", "deployment"],
        evidence=evidence
    )
    
    assert report.coverage_score == 0.75
    assert "deployment" in report.missing_topics
    assert report.needs_more_research is True

@pytest.mark.anyio
async def test_contradiction_detector():
    provider = MockIntelligenceLLMProvider()
    detector = ContradictionDetector(provider)
    
    evidence = [
        EvidenceItem(
            id="1", search_id=1, subquery_id=1, chunk_id="c1", title="React",
            url="https://nextjs.org/docs", domain="nextjs.org", text="Next.js uses App Router for routing.",
            similarity_score=0.8, source_quality_score=0.9
        ),
        EvidenceItem(
            id="2", search_id=1, subquery_id=1, chunk_id="c2", title="React Blog",
            url="https://blog.com", domain="blog.com", text="Next.js only supports Pages Router for routing.",
            similarity_score=0.75, source_quality_score=0.5
        )
    ]
    
    contradictions = await detector.detect_contradictions(
        topics=["routing"],
        evidence=evidence
    )
    
    assert len(contradictions) == 1
    assert contradictions[0].topic == "routing"
    assert contradictions[0].claim_a == "Next.js uses App Router."
    assert contradictions[0].source_b == "https://blog.com"
