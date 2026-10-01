"""Experiment script to analyze cosine similarity score distributions for relevant vs unrelated queries."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from pathlib import Path
from sentence_transformers import util
from app.semantic_search import get_embedding_model, load_embeddings_index

RELEVANT_QUERIES = [
    "financial assistance for students",
    "how to apply for college admission",
    "where can students stay on campus?",
    "where can I borrow textbooks?",
    "when are semester exams?",
]

UNRELATED_QUERIES = [
    "Where can I find information about mango farming?",
    "mango farming",
    "car repair",
    "pizza recipe",
    "weather forecast",
]


def analyze_query(query: str, model, doc_embeddings, metadata):
    query_emb = model.encode(query, convert_to_tensor=True)
    cos_scores = util.cos_sim(query_emb, doc_embeddings)[0]

    scores_with_meta = []
    for idx, score in enumerate(cos_scores):
        scores_with_meta.append((score.item(), metadata[idx]))

    scores_with_meta.sort(key=lambda x: x[0], reverse=True)
    return scores_with_meta


def main():
    index_data = load_embeddings_index()
    if not index_data:
        print("No index data found!")
        return

    doc_embeddings, metadata = index_data
    model = get_embedding_model()

    print("==========================================================================================")
    print("ANALYSIS 1: RELEVANT QUERIES SCORE DISTRIBUTION")
    print("==========================================================================================")
    relevant_top_scores = []
    for q in RELEVANT_QUERIES:
        ranked = analyze_query(q, model, doc_embeddings, metadata)
        top1 = ranked[0]
        top2 = ranked[1] if len(ranked) > 1 else (0, {})
        top3 = ranked[2] if len(ranked) > 2 else (0, {})
        relevant_top_scores.append(top1[0])

        print(f"\n[RELEVANT] Query: \"{q}\"")
        print(f"   Top-1: {top1[1].get('image_name'):28} | Score: {top1[0]:.4f}")
        print(f"   Top-2: {top2[1].get('image_name'):28} | Score: {top2[0]:.4f}")
        print(f"   Top-3: {top3[1].get('image_name'):28} | Score: {top3[0]:.4f}")

    print("\n==========================================================================================")
    print("ANALYSIS 2: UNRELATED QUERIES SCORE DISTRIBUTION (FALSE POSITIVES)")
    print("==========================================================================================")
    unrelated_top_scores = []
    for q in UNRELATED_QUERIES:
        ranked = analyze_query(q, model, doc_embeddings, metadata)
        top1 = ranked[0]
        top2 = ranked[1] if len(ranked) > 1 else (0, {})
        top3 = ranked[2] if len(ranked) > 2 else (0, {})
        unrelated_top_scores.append(top1[0])

        print(f"\n[UNRELATED] Query: \"{q}\"")
        print(f"   Top-1: {top1[1].get('image_name'):28} | Score: {top1[0]:.4f} (False Positive)")
        print(f"   Top-2: {top2[1].get('image_name'):28} | Score: {top2[0]:.4f} (False Positive)")
        print(f"   Top-3: {top3[1].get('image_name'):28} | Score: {top3[0]:.4f} (False Positive)")

    print("\n==========================================================================================")
    print("SUMMARY COMPARISON")
    print("==========================================================================================")
    print(f"Relevant Queries Top-1 Score Range:   {min(relevant_top_scores):.4f} to {max(relevant_top_scores):.4f} (Avg: {sum(relevant_top_scores)/len(relevant_top_scores):.4f})")
    print(f"Unrelated Queries Top-1 Score Range:  {min(unrelated_top_scores):.4f} to {max(unrelated_top_scores):.4f} (Avg: {sum(unrelated_top_scores)/len(unrelated_top_scores):.4f})")
    gap = min(relevant_top_scores) - max(unrelated_top_scores)
    print(f"Margin / Separation Gap between lowest relevant & highest unrelated: {gap:.4f}")


if __name__ == "__main__":
    main()
