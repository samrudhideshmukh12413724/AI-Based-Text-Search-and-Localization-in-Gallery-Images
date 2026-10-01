"""Comprehensive benchmark script comparing Keyword Search, Semantic Search, and Hybrid Search."""

import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
QUERIES_FILE = ROOT / "dataset" / "comprehensive_test_queries.json"

client = TestClient(app)


def evaluate_query(query: str, expected_docs: list[str], search_fn):
    results = search_fn(query)
    retrieved_names = [r.get("image_name") for r in results]

    is_unrelated = len(expected_docs) == 0

    if is_unrelated:
        # For unrelated queries:
        # Success = 0 documents retrieved.
        # Failure (False Positive) = > 0 documents retrieved.
        passed_top1 = (len(retrieved_names) == 0)
        passed_top3 = (len(retrieved_names) == 0)
        fp = 1 if len(retrieved_names) > 0 else 0
        precision = 1.0 if len(retrieved_names) == 0 else 0.0
        recall = 1.0 if len(retrieved_names) == 0 else 0.0
        return {
            "query": query,
            "is_unrelated": True,
            "top1_match": passed_top1,
            "top3_match": passed_top3,
            "retrieved": retrieved_names[:3],
            "expected": expected_docs,
            "precision_at_3": precision,
            "recall_at_3": recall,
            "false_positive": fp,
        }
    else:
        top1_match = len(retrieved_names) > 0 and (retrieved_names[0] in expected_docs)
        top3_match = any(doc in expected_docs for doc in retrieved_names[:3])
        
        top3_retrieved = retrieved_names[:3]
        relevant_in_top3 = [doc for doc in top3_retrieved if doc in expected_docs]
        
        precision = len(relevant_in_top3) / len(top3_retrieved) if top3_retrieved else 0.0
        recall = len(relevant_in_top3) / len(expected_docs) if expected_docs else 0.0

        return {
            "query": query,
            "is_unrelated": False,
            "top1_match": top1_match,
            "top3_match": top3_match,
            "retrieved": top3_retrieved,
            "expected": expected_docs,
            "precision_at_3": precision,
            "recall_at_3": recall,
            "false_positive": 0,
        }


def keyword_search_fn(query: str):
    resp = client.post("/search/keyword", json={"query": query})
    data = resp.json()
    return data.get("results", [])


def semantic_search_fn(query: str):
    resp = client.post("/search/semantic", json={"query": query})
    data = resp.json()
    return data.get("results", [])


def hybrid_search_fn(query: str):
    resp = client.post("/search", json={"query": query})
    data = resp.json()
    return data.get("results", [])


def run_benchmark():
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    categories = bench_data["categories"]
    modes = {
        "Phase 1 Keyword": keyword_search_fn,
        "Phase 2 Semantic": semantic_search_fn,
        "Phase 2 Hybrid": hybrid_search_fn,
    }

    summary_metrics = {}

    for mode_name, fn in modes.items():
        all_evals = []
        cat_metrics = {}

        for cat_name, query_list in categories.items():
            cat_evals = []
            for item in query_list:
                ev = evaluate_query(item["query"], item["expected_docs"], fn)
                cat_evals.append(ev)
                all_evals.append(ev)

            # Compute category level stats
            in_domain = [e for e in cat_evals if not e["is_unrelated"]]
            unrelated = [e for e in cat_evals if e["is_unrelated"]]

            if in_domain:
                top1_acc = sum(1 for e in in_domain if e["top1_match"]) / len(in_domain)
                top3_acc = sum(1 for e in in_domain if e["top3_match"]) / len(in_domain)
            else:
                top1_acc = sum(1 for e in unrelated if e["top1_match"]) / len(unrelated)
                top3_acc = sum(1 for e in unrelated if e["top3_match"]) / len(unrelated)

            cat_metrics[cat_name] = {
                "count": len(cat_evals),
                "top1_acc": top1_acc,
                "top3_acc": top3_acc,
                "fp_count": sum(e["false_positive"] for e in cat_evals),
            }

        # Overall summary
        total_queries = len(all_evals)
        total_in_domain = [e for e in all_evals if not e["is_unrelated"]]
        total_unrelated = [e for e in all_evals if e["is_unrelated"]]

        top1_overall = sum(1 for e in all_evals if e["top1_match"]) / total_queries
        top3_overall = sum(1 for e in all_evals if e["top3_match"]) / total_queries
        avg_precision = sum(e["precision_at_3"] for e in total_in_domain) / len(total_in_domain)
        avg_recall = sum(e["recall_at_3"] for e in total_in_domain) / len(total_in_domain)
        fp_rate = (sum(e["false_positive"] for e in total_unrelated) / len(total_unrelated)) if total_unrelated else 0.0

        summary_metrics[mode_name] = {
            "top1_acc": top1_overall,
            "top3_acc": top3_overall,
            "precision_at_3": avg_precision,
            "recall_at_3": avg_recall,
            "false_positive_rate": fp_rate,
            "categories": cat_metrics,
        }

    # Print Final Comparative Report
    print("\n" + "=" * 95)
    print("      SCIENTIFIC BENCHMARK REPORT: KEYWORD vs SEMANTIC vs HYBRID SEARCH")
    print("=" * 95)

    print("\n--- 1. OVERALL EVALUATION METRICS ---")
    print(f"{'Metric':<25} | {'Keyword':<18} | {'Semantic (Threshold)':<22} | {'Hybrid (Final)':<18}")
    print("-" * 95)
    print(f"{'Top-1 Accuracy':<25} | {summary_metrics['Phase 1 Keyword']['top1_acc']*100:6.1f}%            | {summary_metrics['Phase 2 Semantic']['top1_acc']*100:6.1f}%                | {summary_metrics['Phase 2 Hybrid']['top1_acc']*100:6.1f}%")
    print(f"{'Top-3 Accuracy':<25} | {summary_metrics['Phase 1 Keyword']['top3_acc']*100:6.1f}%            | {summary_metrics['Phase 2 Semantic']['top3_acc']*100:6.1f}%                | {summary_metrics['Phase 2 Hybrid']['top3_acc']*100:6.1f}%")
    print(f"{'Precision@3':<25} | {summary_metrics['Phase 1 Keyword']['precision_at_3']*100:6.1f}%            | {summary_metrics['Phase 2 Semantic']['precision_at_3']*100:6.1f}%                | {summary_metrics['Phase 2 Hybrid']['precision_at_3']*100:6.1f}%")
    print(f"{'Recall@3':<25} | {summary_metrics['Phase 1 Keyword']['recall_at_3']*100:6.1f}%            | {summary_metrics['Phase 2 Semantic']['recall_at_3']*100:6.1f}%                | {summary_metrics['Phase 2 Hybrid']['recall_at_3']*100:6.1f}%")
    print(f"{'False Positive Rate':<25} | {summary_metrics['Phase 1 Keyword']['false_positive_rate']*100:6.1f}%            | {summary_metrics['Phase 2 Semantic']['false_positive_rate']*100:6.1f}%                | {summary_metrics['Phase 2 Hybrid']['false_positive_rate']*100:6.1f}%")

    print("\n--- 2. CATEGORY-BY-CATEGORY BREAKDOWN (Top-3 Accuracy) ---")
    print(f"{'Category':<32} | {'Keyword':<18} | {'Semantic (Threshold)':<22} | {'Hybrid (Final)':<18}")
    print("-" * 95)
    for cat_key in categories.keys():
        kw_acc = summary_metrics['Phase 1 Keyword']['categories'][cat_key]['top3_acc'] * 100
        sem_acc = summary_metrics['Phase 2 Semantic']['categories'][cat_key]['top3_acc'] * 100
        hyb_acc = summary_metrics['Phase 2 Hybrid']['categories'][cat_key]['top3_acc'] * 100
        print(f"{cat_key:<32} | {kw_acc:6.1f}%            | {sem_acc:6.1f}%                | {hyb_acc:6.1f}%")

    print("\n--- 3. OUT-OF-DOMAIN REJECTION VERIFICATION ---")
    print(f"{'Unrelated Query':<45} | {'Expected':<12} | {'Hybrid Result':<25} | {'Verdict'}")
    print("-" * 95)
    for q_item in categories["E_unrelated"]:
        res = hybrid_search_fn(q_item["query"])
        verdict = "PASS (0 Matches)" if len(res) == 0 else f"FAIL ({len(res)} false matches)"
        top_name = res[0]["image_name"] if res else "No relevant documents"
        print(f"{q_item['query']:<45} | 0 Matches    | {top_name:<25} | {verdict}")

    print("=" * 95)


if __name__ == "__main__":
    run_benchmark()
