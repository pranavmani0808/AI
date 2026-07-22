import asyncio
import urllib.request
import json
import time

def call_api(endpoint: str, payload: dict) -> dict:
    url = f"http://localhost:8000{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start_t = time.time()
    try:
        res = urllib.request.urlopen(req, timeout=90)
        data = json.loads(res.read().decode())
        elapsed_ms = int((time.time() - start_t) * 1000)
        data["_elapsed_ms"] = elapsed_ms
        return data
    except Exception as e:
        return {"error": str(e), "_elapsed_ms": int((time.time() - start_t) * 1000)}

def run_all_tests():
    print("==================================================================")
    print("RUNNING 7-SCENARIO INTELLISEARCH BACKEND EVALUATION SUITE")
    print("==================================================================\n")

    results = {}

    # 1. Greeting Query
    print("--> Test 1: Conversational Greeting ('hi')")
    res1 = call_api("/api/search/research", {"query": "hi"})
    results["Test 1: Greeting ('hi')"] = {
        "status": "PASS" if res1.get("intent") == "conversational" and not res1.get("retrieval_used") and len(res1.get("sources", [])) == 0 else "FAIL",
        "intent": res1.get("intent"),
        "retrieval_used": res1.get("retrieval_used"),
        "sources_count": len(res1.get("sources", [])),
        "citations_count": len(res1.get("citations", [])),
        "answer": res1.get("answer"),
        "latency_ms": res1.get("_elapsed_ms")
    }

    # 2. General Knowledge Query
    print("--> Test 2: General Knowledge ('What is RAG?')")
    res2 = call_api("/api/search/research", {"query": "What is RAG?"})
    results["Test 2: General Knowledge ('What is RAG?')"] = {
        "status": "PASS" if res2.get("intent") in ["general_knowledge", "conversational"] and not res2.get("retrieval_used") else "FAIL",
        "intent": res2.get("intent"),
        "retrieval_used": res2.get("retrieval_used"),
        "sources_count": len(res2.get("sources", [])),
        "answer_preview": res2.get("answer", "")[:150] + "...",
        "latency_ms": res2.get("_elapsed_ms")
    }

    # 3. Live Web Search
    print("--> Test 3: Live Web Search ('latest AI news today')")
    res3 = call_api("/api/search/research", {"query": "latest AI news today"})
    results["Test 3: Live Web Search ('latest AI news today')"] = {
        "status": "PASS" if res3.get("retrieval_used") and len(res3.get("sources", [])) > 0 else "FAIL",
        "intent": res3.get("intent"),
        "retrieval_used": res3.get("retrieval_used"),
        "sources_count": len(res3.get("sources", [])),
        "citations_count": len(res3.get("citations", [])),
        "answer_preview": res3.get("answer", "")[:150] + "...",
        "latency_ms": res3.get("_elapsed_ms")
    }

    # 4. Contextual Follow-Up
    print("--> Test 4: Follow-up ('What about performance?')")
    res4 = call_api("/api/search/research", {
        "query": "What about performance?",
        "chat_history": [
            {"role": "user", "content": "Compare React and Next.js"},
            {"role": "assistant", "content": "React is a UI library whereas Next.js is a fullstack React framework."}
        ]
    })
    results["Test 4: Follow-up Reformulation"] = {
        "status": "PASS" if res4.get("reformulated") and res4.get("original_query") == "What about performance?" and "react" in res4.get("standalone_query", "").lower() else "FAIL",
        "original_query": res4.get("original_query"),
        "standalone_query": res4.get("standalone_query"),
        "reformulated": res4.get("reformulated"),
        "retrieval_used": res4.get("retrieval_used"),
        "latency_ms": res4.get("_elapsed_ms")
    }

    # 5. Product Search
    print("--> Test 5: Product Search ('Best phone under ₹70,000 in India')")
    res5 = call_api("/api/search/research", {"query": "Best phone under ₹70,000 in India"})
    results["Test 5: Product Search"] = {
        "status": "PASS" if res5.get("retrieval_used") and len(res5.get("sources", [])) > 0 else "FAIL",
        "intent": res5.get("intent"),
        "sources_count": len(res5.get("sources", [])),
        "top_domains": [s.get("domain") for s in res5.get("sources", [])[:3]],
        "latency_ms": res5.get("_elapsed_ms")
    }

    # 6. Autonomous Research
    print("--> Test 6: Deep Autonomous Research ('RAG vs Long-Context LLMs')")
    res6 = call_api("/api/research/autonomous", {
        "query": "Research the advantages and disadvantages of RAG compared with long-context LLMs"
    })
    results["Test 6: Autonomous Research Pipeline"] = {
        "status": "PASS" if res6.get("iterations", 0) >= 1 and len(res6.get("sources", [])) > 0 else "FAIL",
        "iterations": res6.get("iterations"),
        "subqueries_count": res6.get("subqueries"),
        "sources_count": len(res6.get("sources", [])),
        "coverage_score": res6.get("coverage_score"),
        "citations_count": len(res6.get("citations", [])),
        "latency_ms": res6.get("_elapsed_ms")
    }

    # 7. Obscure Topic Zero-Result Evidence Fallback
    print("--> Test 7: Obscure Topic Zero-Result Evidence Fallback")
    res7 = call_api("/api/research/autonomous", {
        "query": "Research quantum-entangled hyper-dimensional zzzqxx99911999 nonsense"
    })
    results["Test 7: Zero-Result Evidence Fallback"] = {
        "status": "PASS" if len(res7.get("citations", [])) == 0 and "reliable evidence" in res7.get("answer", "").lower() else "FAIL",
        "citations_count": len(res7.get("citations", [])),
        "answer": res7.get("answer"),
        "latency_ms": res7.get("_elapsed_ms")
    }

    print("\n==================================================================")
    print("EVALUATION RESULTS SUMMARY:")
    print("==================================================================")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_all_tests()
