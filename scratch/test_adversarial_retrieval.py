import urllib.request
import json
import time

def call_search(query: str, mode: str = "web") -> dict:
    url = "http://localhost:8000/api/search/research"
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": query, "limit": 10}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        res = urllib.request.urlopen(req, timeout=90)
        data = json.loads(res.read().decode())
        data["_ms"] = int((time.time() - t0) * 1000)
        return data
    except Exception as e:
        return {"error": str(e), "_ms": int((time.time() - t0) * 1000)}

def run_adversarial_tests():
    test_queries = [
        "Recent RAG research papers",
        "React Server Components documentation",
        "Python 3.14 free-threading changes",
        "best gaming laptop under ₹1 lakh India",
        "latest semiconductor news",
        "PostgreSQL vector search documentation",
        "recent research about hallucination detection in LLMs"
    ]

    print("==================================================================")
    print("RUNNING ADVERSARIAL RETRIEVAL EVALUATION SUITE")
    print("==================================================================\n")

    results = {}

    for q in test_queries:
        print(f"--> Testing query: '{q}'...")
        d = call_search(q)
        
        diagnostics = d.get("diagnostics", [])
        sources = d.get("sources", [])
        citations = d.get("citations", [])
        
        selected_diag = [diag for diag in diagnostics if diag.get("selected")]
        rejected_diag = [diag for diag in diagnostics if not diag.get("selected")]
        
        selected_domains = [diag.get("domain") for diag in selected_diag]
        rejected_domains = [f"{diag.get('domain')} (Low intent score / cap)" for diag in rejected_diag[:3]]
        source_types = list(set([diag.get("source_type") for diag in selected_diag]))
        semantic_scores = [diag.get("post_crawl_score") for diag in selected_diag]
        
        results[q] = {
            "intent": d.get("intent"),
            "generated_search_queries": [d.get("standalone_query", q)],
            "candidate_count": len(diagnostics),
            "crawled_count": len(sources),
            "rejected_domains_with_reasons": rejected_domains,
            "selected_domains": selected_domains,
            "source_types": source_types,
            "semantic_scores": semantic_scores,
            "citations_count": len(citations),
            "latency_ms": d.get("_ms")
        }

    print("\n==================================================================")
    print("ADVERSARIAL RETRIEVAL EVALUATION REPORT:")
    print("==================================================================")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_adversarial_tests()
