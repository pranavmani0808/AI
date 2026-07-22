import re
from typing import List, Dict, Any, Optional
from backend.llm.provider import LLMProvider

async def evaluate_answer(
    answer: str,
    query: str,
    expected_topics: List[str],
    provider: Optional[LLMProvider] = None
) -> Dict[str, Any]:
    """
    Evaluates response answer quality:
    - completeness: % of expected keywords/topics found in answer text.
    - claim_risk: % of sentences without citation markers.
    - llm_groundedness (Optional): Labeled explicitly as "LLM-evaluated" using Gemini check.
    """
    # 1. Calculate completeness
    answer_lower = answer.lower()
    found_topics = 0
    for topic in expected_topics:
        if topic.lower() in answer_lower:
            found_topics += 1
            
    completeness = (found_topics / len(expected_topics)) if expected_topics else 1.0
    
    # 2. Unsupported claim risk (sentences without citation bracket [N] or [src_N])
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
    total_sentences = len(sentences)
    unsupported_sentences = 0
    for s in sentences:
        if not re.search(r'\[[a-zA-Z0-9_\-]+\]', s):
            unsupported_sentences += 1
            
    claim_risk = (unsupported_sentences / total_sentences) if total_sentences > 0 else 0.0
    
    # 3. LLM-assisted evaluation
    llm_groundedness_score = None
    if provider:
        try:
            # Explicitly label LLM-evaluated context verification
            eval_prompt = (
                f"Query: {query}\n"
                f"Generated Answer: {answer}\n\n"
                f"Assess whether the Generated Answer contains claims that are not backed by any source citations. "
                f"Return a single JSON block: "
                f'{{"groundedness_score": float, "reasoning": str}} '
                f"where groundedness_score is between 0.0 (unsupported) and 1.0 (fully grounded)."
            )
            response = await provider.generate(
                system_instruction="You are an LLM-evaluated answer groundedness quality auditor. Assess the text and output JSON only.",
                prompt=eval_prompt
            )
            # Parse score safely
            match = re.search(r'"groundedness_score"\s*:\s*([0-9\.]+)', response)
            if match:
                llm_groundedness_score = float(match.group(1))
        except Exception as e:
            print(f"LLM-assisted answer evaluation skipped: {e}")
            
    return {
        "completeness": completeness,
        "unsupported_claim_risk": claim_risk,
        "llm_evaluated_groundedness": llm_groundedness_score
    }
