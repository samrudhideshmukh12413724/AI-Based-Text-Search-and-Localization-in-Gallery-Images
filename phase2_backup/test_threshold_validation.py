"""Validation script to verify similarity threshold on relevant and unrelated queries."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

RELEVANT_TESTS = [
    ("financial assistance for students", ["scholarship", "loan"]),
    ("how to apply for college admission", ["admission"]),
    ("where can students stay on campus?", ["hostel"]),
    ("where can I borrow textbooks?", ["library"]),
    ("when are semester exams?", ["exam", "timetable"]),
]

UNRELATED_TESTS = [
    "Where can I find information about mango farming?",
    "mango farming",
    "car repair",
    "pizza recipe",
    "weather forecast",
]


def test_all():
    print("==========================================================================================")
    print("1. VALIDATING RELEVANT QUERIES (Threshold >= 0.35)")
    print("==========================================================================================")
    all_relevant_passed = True
    for query, expected_keywords in RELEVANT_TESTS:
        resp = client.post("/search/semantic", json={"query": query})
        data = resp.json()
        count = data.get("count", 0)
        results = data.get("results", [])

        if count > 0:
            top_img = results[0]["image_name"]
            top_score = results[0]["similarity_score"]
            is_valid = any(kw in top_img.lower() for kw in expected_keywords)
            status = "PASS" if is_valid else "CHECK"
            print(f"[{status}] Query: \"{query}\"")
            print(f"       Found {count} matches | Top-1: {top_img} (Score: {top_score:.4f})")
            if not is_valid:
                all_relevant_passed = False
        else:
            print(f"[FAIL] Query: \"{query}\" -> Returned 0 results!")
            all_relevant_passed = False

    print("\n==========================================================================================")
    print("2. VALIDATING UNRELATED QUERIES (Threshold Filtering)")
    print("==========================================================================================")
    all_unrelated_passed = True
    for query in UNRELATED_TESTS:
        resp = client.post("/search/semantic", json={"query": query})
        data = resp.json()
        count = data.get("count", 0)
        msg = data.get("message", "")

        if count == 0:
            print(f"[PASS] Query: \"{query}\"")
            print(f"       Matches: 0 | Message: \"{msg}\"")
        else:
            top_img = data["results"][0]["image_name"]
            top_score = data["results"][0]["similarity_score"]
            print(f"[FAIL] Query: \"{query}\" -> Unexpected False Positive: {top_img} (Score: {top_score:.4f})")
            all_unrelated_passed = False

    print("\n==========================================================================================")
    print("3. VALIDATING KEYWORD SEARCH (/search/keyword)")
    print("==========================================================================================")
    resp_kw = client.post("/search/keyword", json={"query": "scholarship"})
    kw_count = resp_kw.json().get("count", 0)
    print(f"Keyword search for 'scholarship': {kw_count} matches -> {'PASS' if kw_count > 0 else 'FAIL'}")

    print("\n==========================================================================================")
    print("4. VALIDATING HYBRID SEARCH FALLBACK (/search)")
    print("==========================================================================================")
    # 1. Exact keyword match
    resp_hybrid_kw = client.post("/search", json={"query": "scholarship"})
    print(f"Hybrid on exact word 'scholarship': {resp_hybrid_kw.json().get('count', 0)} matches")

    # 2. Semantic match without keyword
    resp_hybrid_sem = client.post("/search", json={"query": "financial assistance for students"})
    print(f"Hybrid on natural query 'financial assistance': {resp_hybrid_sem.json().get('count', 0)} matches (Top: {resp_hybrid_sem.json().get('results', [{}])[0].get('image_name')})")

    # 3. Unrelated query
    resp_hybrid_none = client.post("/search", json={"query": "Where can I find information about mango farming?"})
    print(f"Hybrid on unrelated 'mango farming': {resp_hybrid_none.json().get('count', 0)} matches (Message: \"{resp_hybrid_none.json().get('message')}\")")

    print("\n==========================================================================================")
    if all_relevant_passed and all_unrelated_passed and kw_count > 0:
        print("ALL THRESHOLD VALIDATION TESTS PASSED SUCCESSFULLY! (100% Accuracy, 0% False Positives)")
    else:
        print("SOME TESTS FAILED! Review output above.")
    print("==========================================================================================")


if __name__ == "__main__":
    test_all()
