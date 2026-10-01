import sys
import io
from pathlib import Path

# Fix stdout encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.semantic_search import semantic_search
from app.main import search_images
from pydantic import BaseModel

class SearchReq(BaseModel):
    query: str

def test_calibrated_threshold():
    valid_cases = [
        ("financial aid for students", ["scholarship", "loan"]),
        ("where can students live", ["hostel"]),
        ("where can I borrow books", ["library"]),
        ("when are semester exams", ["exam", "timetable"]),
        ("how to apply for college", ["admission"]),
    ]

    invalid_cases = [
        "birthday party",
        "mango farming",
        "pizza recipe",
        "car repair",
        "weather forecast",
        "dog training",
    ]

    print("=" * 80)
    print("TESTING VALID QUERIES (Expected: Matches Returned >= 1 with High Relevance)")
    print("=" * 80)
    valid_passed = 0
    for query, expected_keywords in valid_cases:
        res = search_images(SearchReq(query=query))
        count = res.get("count", 0)
        results = res.get("results", [])
        if count > 0:
            top_doc = results[0]["image_name"]
            score = results[0].get("similarity_score", "N/A")
            print(f"[PASS] VALID QUERY: '{query}' -> Found {count} doc(s) | Top: {top_doc} (Score: {score})")
            valid_passed += 1
        else:
            print(f"[FAIL] VALID QUERY: '{query}' -> 0 matches found!")

    print("\n" + "=" * 80)
    print("TESTING INVALID / OUT-OF-DOMAIN QUERIES (Expected: 0 Matches -> Clean Empty State)")
    print("=" * 80)
    invalid_passed = 0
    for query in invalid_cases:
        res = search_images(SearchReq(query=query))
        count = res.get("count", 0)
        msg = res.get("message", "")
        if count == 0:
            print(f"[PASS] INVALID QUERY: '{query}' -> Correctly Rejected! (Count: 0, Message: '{msg}')")
            invalid_passed += 1
        else:
            top_doc = res["results"][0]["image_name"]
            score = res["results"][0].get("similarity_score", "N/A")
            print(f"[FAIL] INVALID QUERY: '{query}' -> FALSE POSITIVE: {top_doc} (Score: {score})")

    print("\n" + "=" * 80)
    print(f"SUMMARY: Valid: {valid_passed}/{len(valid_cases)} Passed | Invalid: {invalid_passed}/{len(invalid_cases)} Passed")
    print("=" * 80)

if __name__ == "__main__":
    test_calibrated_threshold()
