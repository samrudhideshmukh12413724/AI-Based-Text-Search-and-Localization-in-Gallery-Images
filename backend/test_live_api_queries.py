import io
import json
import sys
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=" * 85)
    print("TESTING LIVE UNIFIED MULTI-MODAL BACKEND SEARCH API")
    print("=" * 85)

    queries = [
        ("signature", "Visual Region Search"),
        ("official stamp", "Visual Region Search"),
        ("photograph", "Visual Region Search"),
        ("scholarship", "Semantic NLP Search"),
        ("mango farming", "Negative Control Rejection")
    ]

    for q, test_type in queries:
        print(f"\n--- Testing Query: '{q}' [{test_type}] ---")
        resp = requests.post(f"{BASE_URL}/search", json={"query": q}, timeout=10)
        data = resp.json()
        print(f"Status Code: {resp.status_code} | Search Type: {data.get('search_type')} | Matches: {data.get('count')}")
        for i, item in enumerate(data.get("results", [])[:2]):
            v_objs = item.get("visual_objects", [])
            bbox_info = v_objs[0].get("normalized_bbox") if v_objs else "None"
            loc = v_objs[0].get("location_desc") if v_objs else "N/A"
            print(f"  [{i+1}] {item.get('image_name'):<22} | Score: {item.get('similarity_score')} | Loc: {loc} | BBox: {bbox_info}")

    print("\n" + "=" * 85)
    print("LIVE MULTI-MODAL API VERIFICATION COMPLETE!")
    print("=" * 85)

if __name__ == "__main__":
    test_api()
