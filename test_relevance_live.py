import requests
import time
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"

test_suite = [
    {
        "category": "1. Exact Keyword Match",
        "query": "scholarship",
        "description": "Direct token match in document corpus",
        "expected_intent": "Should retrieve scholarship.jpg with 1.00 score and keyword search type"
    },
    {
        "category": "2. Typo-Tolerant Fuzzy Match",
        "query": "scholrship",
        "description": "OCR character dropout / spelling mistake ('scholrship')",
        "expected_intent": "Damerau-Levenshtein fuzzy logic should recover scholarship document"
    },
    {
        "category": "3. Dense Semantic Concept (Zero Keyword Overlap)",
        "query": "financial assistance for university students",
        "description": "Abstract concept query with zero lexical match to 'scholarship'",
        "expected_intent": "SentenceTransformers (all-MiniLM-L6-v2) semantic cosine similarity retrieval"
    },
    {
        "category": "4. Inflection & Synonyms Mapping",
        "query": "hostel room allocation fee",
        "description": "Compound inflection across hostel and fee challan documents",
        "expected_intent": "Should retrieve hostel and fees documents with high ranking"
    },
    {
        "category": "5. Multi-Modal Visual + Text Dual Match",
        "query": "student identity card",
        "description": "Grounded ID card query requiring text + visual portrait/seal",
        "expected_intent": "Should match identity cards and return visual object bounding box"
    },
    {
        "category": "6. Out-of-Distribution Hallucination Rejection (Negative Control)",
        "query": "quantum teleportation and mango farming",
        "description": "Completely irrelevant nonsense query",
        "expected_intent": "Adaptive thresholding should REJECT all candidates (0 results or < cutoff)"
    }
]

print("=" * 95)
print("DOCULENS AI - LIVE RELEVANCE & ACCURACY BENCHMARK AUDIT")
print("=" * 95)

results_summary = []

for item in test_suite:
    q = item["query"]
    cat = item["category"]
    print(f"\n▶ [{cat}]")
    print(f"  Query:       '{q}'")
    print(f"  Description: {item['description']}")
    
    t0 = time.perf_counter()
    try:
        resp = requests.post(f"{BASE_URL}/search", json={"query": q}, timeout=30)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        data = resp.json()
        matches = data.get("results", [])
        search_type = data.get("search_type", "unknown")
        
        print(f"  Status:      HTTP {resp.status_code} | Latency: {elapsed_ms:.1f}ms | Matches: {len(matches)}")
        print(f"  Search Mode: {search_type}")
        
        if matches:
            top = matches[0]
            score = top.get("similarity_score", 0.0)
            img = top.get("image_name", "N/A")
            preview = top.get("matched_text", top.get("preview_snippet", ""))[:60].replace("\n", " ")
            has_vis = top.get("has_visual_objects", False)
            terms = top.get("highlight_terms", [])
            print(f"  Top Match:   {img} (Score: {score:.3f}, Visual Grounded: {has_vis})")
            print(f"  Highlights:  {terms[:3]} | Snippet: \"{preview}...\"")
            results_summary.append({
                "category": cat, "query": q, "status": "HIT", "matches": len(matches),
                "top_doc": img, "score": score, "type": search_type, "latency_ms": elapsed_ms
            })
        else:
            print(f"  Top Match:   NONE (Clean Rejection - No Hallucination)")
            results_summary.append({
                "category": cat, "query": q, "status": "REJECTED (CLEAN)", "matches": 0,
                "top_doc": "None", "score": 0.0, "type": search_type, "latency_ms": elapsed_ms
            })
    except Exception as e:
        print(f"  Error: {e}")
        results_summary.append({
            "category": cat, "query": q, "status": f"ERROR: {e}", "matches": 0,
            "top_doc": "Error", "score": 0.0, "type": "error", "latency_ms": 0.0
        })

print("\n" + "=" * 95)
print("AUDIT SUMMARY MATRIX")
print("=" * 95)
print(f"{'Category':<32} | {'Query':<28} | {'Outcome':<14} | {'Top Result':<20} | {'Score'}")
print("-" * 105)
for r in results_summary:
    cat_short = r['category'].split('.')[1].strip()[:30] if '.' in r['category'] else r['category'][:30]
    print(f"{cat_short:<32} | {r['query']:<28} | {r['status']:<14} | {r['top_doc'][:20]:<20} | {r['score']:.3f}")
print("=" * 95)
