import re
from typing import List, Tuple, Set
from backend.llm.models import GroundingEvidence, Citation
from backend.llm.provider import LLMProvider

def extract_citation_indices(text: str) -> Set[int]:
    """Helper to extract unique numeric citation indices from bracketed text, e.g. [1], [2]."""
    matches = re.findall(r'\[(\d+)\]', text)
    return {int(idx) for idx in matches}

async def validate_and_repair_citations(
    answer: str,
    evidences: List[GroundingEvidence],
    provider: LLMProvider
) -> Tuple[str, List[Citation], bool]:
    """
    Validates and repairs citation index references:
    - Extracts inline citation markers [N]
    - Checks indexes N against available evidence list
    - If invalid citations exist, triggers a one-time controlled repair pass via the LLM provider
    - Checks the repaired output. If still invalid, falls back to the safe insufficient evidence response
    - Populates the final Citation models using only verified backend URL metadata
    """
    valid_indices = {e.citation_id for e in evidences}
    
    # Empty evidence edge case
    if not evidences:
        return (
            "I couldn't find enough reliable evidence in the retrieved sources to answer this confidently.",
            [],
            False
        )

    # 1. First Validation Pass
    used_indices = extract_citation_indices(answer)
    invalid_indices = used_indices - valid_indices
    
    # If all citations are valid, proceed to build response
    if not invalid_indices:
        return build_citations_response(answer, evidences)

    # 2. Trigger Controlled Repair Pass
    print(f"Invalid citations detected: {invalid_indices}. Executing repair pass...")
    
    repair_system_instruction = (
        "You are an expert citation repair assistant. Your task is to edit the provided draft answer. "
        "Correct any citation markers [N] that do not match the allowed valid evidence IDs. "
        "You must ONLY use indices from the allowed valid list. "
        "If a statement or claim in the text cannot be supported by any allowed source, rewrite "
        "or remove the statement to ensure the response remains 100% grounded in facts. "
        "Do not invent citation numbers or URLs."
    )
    
    allowed_sources_str = ", ".join([str(idx) for idx in sorted(valid_indices)])
    prompt = (
        f"Allowed Valid Evidence IDs: {allowed_sources_str}\n\n"
        f"Draft Answer containing invalid citations:\n{answer}\n\n"
        f"Please output only the corrected grounded answer text below, with correct citations:"
    )
    
    try:
        repaired_answer = await provider.generate(repair_system_instruction, prompt)
        repaired_answer = repaired_answer.strip()
        
        # 3. Second Validation Pass on Repaired Text
        used_repaired_indices = extract_citation_indices(repaired_answer)
        still_invalid_indices = used_repaired_indices - valid_indices
        
        if not still_invalid_indices:
            print("Citation repair successful.")
            return build_citations_response(repaired_answer, evidences)
            
        print(f"Citation repair failed. Invalid indexes still present: {still_invalid_indices}. Rejecting answer.")
    except Exception as e:
        print(f"Citation repair API request failed: {e}")

    # 4. Fallback on Double Validation Failure
    return (
        "I couldn't find enough reliable evidence in the retrieved sources to answer this confidently.",
        [],
        False
    )

def build_citations_response(
    answer_text: str,
    evidences: List[GroundingEvidence]
) -> Tuple[str, List[Citation], bool]:
    """Helper to map active citation IDs in verified text to Citation models."""
    used_indices = extract_citation_indices(answer_text)
    
    final_citations = []
    evidence_map = {e.citation_id: e for e in evidences}
    
    for idx in sorted(used_indices):
        evidence = evidence_map.get(idx)
        if evidence:
            final_citations.append(Citation(
                id=idx,
                title=evidence.title,
                url=evidence.url,
                domain=evidence.domain,
                chunk_id=evidence.chunk_id
            ))
            
    # Check if there is any text, default grounded to true
    is_grounded = len(final_citations) > 0 or "I couldn't find enough" not in answer_text
    
    return answer_text, final_citations, is_grounded
