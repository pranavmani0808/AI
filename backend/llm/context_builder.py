from typing import List, Tuple
from backend.rag.models import RetrievedChunk
from backend.llm.models import GroundingEvidence
from backend.core.config import settings

def build_grounding_context(
    chunks: List[RetrievedChunk],
    min_score: float = None,
    max_chunks: int = None,
    max_chars: int = None
) -> Tuple[str, List[GroundingEvidence]]:
    """
    Transforms retrieved vector database chunks into an XML-delimited context prompt:
    - Applies minimum similarity score filters (RAG_MIN_SCORE)
    - Filters out duplicate passages (deduplication on normalized text)
    - Binds context by count (RAG_MAX_CONTEXT_CHUNKS) and character budget (RAG_MAX_CONTEXT_CHARS)
    - Builds a clean list of GroundingEvidence models with sequential user-facing citation IDs
    """
    score_thresh = min_score if min_score is not None else settings.RAG_MIN_SCORE
    chunks_limit = max_chunks if max_chunks is not None else settings.RAG_MAX_CONTEXT_CHUNKS
    chars_limit = max_chars if max_chars is not None else settings.RAG_MAX_CONTEXT_CHARS
    
    # 1. Score filter & Sort descending
    valid_chunks = [c for c in chunks if c.score >= score_thresh]
    valid_chunks.sort(key=lambda x: x.score, reverse=True)
    
    seen_texts = set()
    grounding_evidences: List[GroundingEvidence] = []
    
    context_blocks = []
    current_char_count = 0
    citation_id = 1
    
    for chunk in valid_chunks:
        # Enforce max chunks limit
        if len(grounding_evidences) >= chunks_limit:
            break
            
        # Clean text signature for duplication check
        clean_text = chunk.text.strip()
        text_signature = " ".join(clean_text.lower().split())[:150]
        if text_signature in seen_texts:
            continue
            
        # Format XML context element for prompt injection shield
        block = (
            f'<evidence id="{citation_id}">\n'
            f'Title: {chunk.title}\n'
            f'URL: {chunk.url}\n'
            f'Domain: {chunk.domain}\n'
            f'Content:\n{chunk.text}\n'
            f'</evidence>'
        )
        
        # Enforce character count budget check
        if current_char_count + len(block) > chars_limit:
            break
            
        seen_texts.add(text_signature)
        context_blocks.append(block)
        current_char_count += len(block)
        
        # Save evidence metadata
        grounding_evidences.append(GroundingEvidence(
            citation_id=citation_id,
            chunk_id=chunk.id,
            search_id=chunk.search_id,
            title=chunk.title,
            url=chunk.url,
            domain=chunk.domain,
            text=chunk.text,
            score=chunk.score
        ))
        
        citation_id += 1
        
    context_str = "\n\n".join(context_blocks)
    return context_str, grounding_evidences
