import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.semantic_search import semantic_search

def analyze_thresholds():
    valid_queries = [
        ("financial aid for students", "scholarship"),
        ("where can students live", "hostel"),
        ("where can I borrow books", "library"),
        ("when are semester exams", "exam"),
        ("how to apply for college", "admission"),
    ]

    invalid_queries = [
        "birthday party",
        "mango farming",
        "pizza recipe",
        "car repair",
        "weather forecast",
        "dog training",
    ]

    print("=" * 80)
    print("ANALYSIS OF VALID ACADEMIC QUERIES (Scores of Top-1 Matched Document)")
    print("=" * 80)

    valid_top_scores = []
    for query, expected_cat in valid_queries:
        # Search with threshold 0.0 to inspect full cosine similarity distribution
        results = semantic_search(query, top_k=5, min_score=0.0)
        if results:
            top_match = results[0]
            score = top_match["similarity_score"]
            name = top_match.get("image_name") or Path(top_match.get("image_path", "")).name
            valid_top_scores.append((query, name, score))
            print(f"Query: '{query:<35}' -> Top Doc: {name:<32} | Score: {score:.4f}")
        else:
            print(f"Query: '{query}' -> NO RESULTS")

    print("\n" + "=" * 80)
    print("ANALYSIS OF INVALID / OUT-OF-DOMAIN QUERIES (Max Cosine Similarity in Entire DB)")
    print("=" * 80)

    invalid_top_scores = []
    for query in invalid_queries:
        results = semantic_search(query, top_k=5, min_score=0.0)
        if results:
            top_match = results[0]
            score = top_match["similarity_score"]
            name = top_match.get("image_name") or Path(top_match.get("image_path", "")).name
            invalid_top_scores.append((query, name, score))
            print(f"Query: '{query:<35}' -> Max Doc: {name:<32} | Score: {score:.4f}")
        else:
            print(f"Query: '{query}' -> NO RESULTS")

    print("\n" + "=" * 80)
    print("EMPIRICAL THRESHOLD OPTIMIZATION")
    print("=" * 80)

    min_valid = min(score for _, _, score in valid_top_scores)
    max_invalid = max(score for _, _, score in invalid_top_scores)

    print(f"Minimum Top-1 Score for Valid Queries   : {min_valid:.4f}")
    print(f"Maximum False-Positive Score for Invalid : {max_invalid:.4f}")
    print(f"Margin Separation Gap                   : {min_valid - max_invalid:+.4f}")

    print("\nCandidate Threshold Evaluation:")
    for t in [0.35, 0.38, 0.39, 0.40, 0.42, 0.44, 0.45]:
        valid_passed = sum(1 for _, _, s in valid_top_scores if s >= t)
        invalid_rejected = sum(1 for _, _, s in invalid_top_scores if s < t)
        print(
            f"  Threshold tau = {t:.2f} -> Valid Retained: {valid_passed}/{len(valid_queries)} "
            f"({valid_passed/len(valid_queries)*100:5.1f}%) | "
            f"Invalid Rejected: {invalid_rejected}/{len(invalid_queries)} "
            f"({invalid_rejected/len(invalid_queries)*100:5.1f}%)"
        )

if __name__ == "__main__":
    analyze_thresholds()
