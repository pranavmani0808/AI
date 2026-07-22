from typing import List, Dict, Any
from urllib.parse import urlparse

def evaluate_retrieval(chunks: List[Any]) -> Dict[str, Any]:
    """
    Evaluates vector store retrieval quality:
    - top_k: total count of retrieved evidence chunks
    - avg_similarity: average cosine similarity score
    - max_similarity: highest similarity score
    - min_similarity: lowest similarity score
    - unique_domains: number of unique source domains retrieved
    """
    total_retrieved = len(chunks)
    if total_retrieved == 0:
        return {
            "top_k": 0,
            "avg_similarity": 0.0,
            "max_similarity": 0.0,
            "min_similarity": 0.0,
            "unique_domains": 0
        }
        
    scores = []
    domains = set()
    
    for c in chunks:
        # Check standard score attributes (e.g. score or similarity_score)
        score = getattr(c, "score", getattr(c, "similarity_score", 0.0))
        scores.append(score)
        
        url = getattr(c, "url", "")
        if url:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            domains.add(domain)
            
    return {
        "top_k": total_retrieved,
        "avg_similarity": round(sum(scores) / total_retrieved, 3),
        "max_similarity": round(max(scores), 3),
        "min_similarity": round(min(scores), 3),
        "unique_domains": len(domains)
    }
