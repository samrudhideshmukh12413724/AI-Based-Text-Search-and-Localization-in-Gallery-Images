"""Evaluate Phase 1 Keyword Search vs Phase 2 Semantic Search on benchmark queries."""

import json
from pathlib import Path

from app.database import search_by_keyword
from app.semantic_search import semantic_search

ROOT = Path(__file__).resolve().parents[1]
TEST_QUERIES_FILE = ROOT / "dataset" / "test_queries.json"
EVALUATION_REPORT = ROOT / "dataset" / "evaluation_report.json"


def main():
    if not TEST_QUERIES_FILE.exists():
        print(f"Error: {TEST_QUERIES_FILE} not found!")
        return

    with open(TEST_QUERIES_FILE, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    queries = benchmark.get("queries", [])
    print(f"================================================================================")
    print(f"BENCHMARK EVALUATION: Phase 1 (Keyword) vs Phase 2 (Semantic Search)")
    print(f"Total Benchmark Queries: {len(queries)}")
    print(f"================================================================================\n")

    kw_success_count = 0
    sem_success_count = 0
    comparisons = []

    for q in queries:
        qid = q["query_id"]
        query_str = q["query"]
        expected_images = [img.lower() for img in q["expected_images"]]

        # Phase 1: Keyword search
        kw_results = search_by_keyword(query_str)
        kw_filenames = [Path(r["image_path"]).name.lower() for r in kw_results]
        kw_hit = any(expected in kw_filenames[:3] for expected in expected_images)
        if kw_hit:
            kw_success_count += 1

        # Phase 2: Semantic search
        sem_results = semantic_search(query_str, top_k=5)
        sem_filenames = [Path(r["image_path"]).name.lower() for r in sem_results]
        sem_hit = any(expected in sem_filenames[:3] for expected in expected_images)
        if sem_hit:
            sem_success_count += 1

        top_sem_match = sem_results[0] if sem_results else {}
        top_sem_name = Path(top_sem_match.get("image_path", "")).name if top_sem_match else "None"
        top_sem_score = top_sem_match.get("similarity_score", 0.0)

        kw_status = "PASS" if kw_hit else "FAIL"
        sem_status = "PASS" if sem_hit else "FAIL"

        print(f"[{qid}] Query: \"{query_str}\"")
        print(f"      Expected: {', '.join(expected_images)}")
        print(f"      Keyword Search:  [{kw_status}] -> Found {len(kw_results)} results")
        print(f"      Semantic Search: [{sem_status}] -> Top 1: {top_sem_name} (Score: {top_sem_score:.4f})")
        print(f"      -------------------------------------------------------------------------")

        comparisons.append({
            "query_id": qid,
            "query": query_str,
            "expected_images": expected_images,
            "keyword_search": {
                "is_hit": kw_hit,
                "total_results": len(kw_results),
                "top_matches": kw_filenames[:3]
            },
            "semantic_search": {
                "is_hit": sem_hit,
                "total_results": len(sem_results),
                "top_matches": [
                    {"filename": Path(r["image_path"]).name, "score": r.get("similarity_score")}
                    for r in sem_results[:3]
                ]
            }
        })

    kw_acc = round((kw_success_count / len(queries)) * 100, 1)
    sem_acc = round((sem_success_count / len(queries)) * 100, 1)

    print("\n================================================================================")
    print("FINAL BENCHMARK COMPARISON RESULTS")
    print("================================================================================")
    print(f"Phase 1 (Keyword Search) Accuracy (Top-3):  {kw_success_count}/{len(queries)} ({kw_acc}%)")
    print(f"Phase 2 (Semantic Search) Accuracy (Top-3): {sem_success_count}/{len(queries)} ({sem_acc}%)")
    print(f"Accuracy Improvement: +{round(sem_acc - kw_acc, 1)}%")
    print("================================================================================\n")

    report = {
        "total_queries": len(queries),
        "keyword_search_accuracy_percent": kw_acc,
        "semantic_search_accuracy_percent": sem_acc,
        "improvement_percent": round(sem_acc - kw_acc, 1),
        "details": comparisons
    }

    with open(EVALUATION_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Detailed comparison report saved to: {EVALUATION_REPORT}")


if __name__ == "__main__":
    main()
