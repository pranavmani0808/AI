import urllib.request
import json
import time

def call_search_api(query: str) -> dict:
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
        data["_elapsed_ms"] = int((time.time() - t0) * 1000)
        return data
    except Exception as e:
        return {"error": str(e), "_elapsed_ms": int((time.time() - t0) * 1000)}

def evaluate_retrieval_quality():
    test_queries = [
        "Best phone under ₹70,000 in India",
        "iPhone 16 price in India",
        "React vs Next.js performance",
        "Latest OpenAI news today",
        "Recent RAG research papers",
        "Who won the latest Formula 1 race?"
    ]

    print("==================================================================")
    print("RUNNING RETRIEVAL QUALITY & SOURCE RELEVANCE EVALUATION SUITE")
    print("==================================================================\n")

    summary = {}

    for q in test_queries:
        print(f"--> Evaluating: '{q}'...")
        res = call_search_api(q)
        
        sources = res.get("sources", [])
        citations = res.get("citations", [])
        diagnostics = res.get("diagnostics", [])
        domains = [s.get("domain") for s in sources]
        
        # Check source quality criteria
        has_sources = len(sources) > 0
        has_citations = len(citations) > 0
        
        summary[q] = {
            "intent": res.get("intent"),
            "retrieval_used": res.get("retrieval_used"),
            "sources_count": len(sources),
            "citations_count": len(citations),
            "top_domains": domains[:4],
            "diagnostics_count": len(diagnostics),
            "latency_ms": res.get("_elapsed_ms"),
            "answer_snippet": res.get("answer", "")[:120] + "..." if res.get("answer") else "N/A"
        }

    print("\n==================================================================")
    print("RETRIEVAL QUALITY EVALUATION SUMMARY:")
    print("==================================================================")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    evaluate_retrieval_quality()
