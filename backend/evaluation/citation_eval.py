import re
from typing import List, Dict, Any, Set
from backend.llm.models import Citation, GroundingEvidence

def evaluate_citations(
    answer: str,
    citations: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates the integrity of the generated citations:
    - citation_validity: % of citations mapping to real evidence chunks.
    - citation_coverage: % of factual answer sentences backed by citation markers.
    - citation_source_diversity: number of unique domains cited.
    """
    total_citations = len(citations)
    if total_citations == 0:
        return {
            "citation_validity": 1.0,
            "citation_coverage": 0.0,
            "citation_source_diversity": 0
        }
        
    # Build set of valid evidence IDs
    valid_evidence_ids: Set[str] = {ev["id"] for ev in evidences}
    
    # 1. Calculate validity
    valid_citations_count = 0
    for cit in citations:
        # Match evidenceId reference
        if cit.get("evidenceId") in valid_evidence_ids:
            valid_citations_count += 1
            
    citation_validity = valid_citations_count / total_citations
    
    # 2. Calculate coverage: check sentences containing factual assertions
    # Split text by standard sentence delimiters (. ! ?)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
    total_sentences = len(sentences)
    
    sentences_with_citations = 0
    for s in sentences:
        # Check if sentence contains standard bracket citations (e.g., [1], [src_1], etc.)
        if re.search(r'\[[a-zA-Z0-9_\-]+\]', s):
            sentences_with_citations += 1
            
    citation_coverage = (sentences_with_citations / total_sentences) if total_sentences > 0 else 0.0
    
    # 3. Calculate source diversity
    cited_source_ids = {cit.get("sourceId") for cit in citations if cit.get("sourceId")}
    
    return {
        "citation_validity": citation_validity,
        "citation_coverage": citation_coverage,
        "citation_source_diversity": len(cited_source_ids)
    }
