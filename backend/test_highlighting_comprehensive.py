"""Comprehensive automated test suite for Keyword & Semantic Highlighting and Smart Text Previews."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_suite():
    print("=" * 90)
    print("      COMPREHENSIVE HIGHLIGHTING & SMART TEXT PREVIEW TEST SUITE")
    print("=" * 90)

    passed_count = 0
    total_tests = 7

    # -------------------------------------------------------------
    # Test 1 — Exact Keyword
    # -------------------------------------------------------------
    print("\n[TEST 1] Exact Keyword Highlighting")
    q1 = "cricket"
    r1 = client.post("/search", json={"query": q1}).json()
    res1 = r1.get("results", [])
    t1_pass = len(res1) > 0 and any("cricket" in t.lower() for t in res1[0].get("highlight_terms", []))
    print(f"  Query: \"{q1}\"")
    if res1:
        print(f"  Doc: {res1[0].get('image_name')}")
        print(f"  Preview: \"{res1[0].get('preview_snippet')}\"")
        print(f"  Highlight Terms: {res1[0].get('highlight_terms')}")
    print(f"  Result: {'PASSED' if t1_pass else 'FAILED'}")
    if t1_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 2 — Case Difference
    # -------------------------------------------------------------
    print("\n[TEST 2] Case Difference Highlighting")
    q2 = "SCHOLARSHIP"
    r2 = client.post("/search", json={"query": q2}).json()
    res2 = r2.get("results", [])
    t2_pass = len(res2) > 0 and any("scholarship" in t.lower() for t in res2[0].get("highlight_terms", []))
    print(f"  Query: \"{q2}\"")
    if res2:
        print(f"  Doc: {res2[0].get('image_name')}")
        print(f"  Preview: \"{res2[0].get('preview_snippet')}\"")
        print(f"  Highlight Terms: {res2[0].get('highlight_terms')}")
    print(f"  Result: {'PASSED' if t2_pass else 'FAILED'}")
    if t2_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 3 — Semantic Highlighting
    # -------------------------------------------------------------
    print("\n[TEST 3] Semantic Phrase Highlighting (Synonym Query)")
    q3 = "financial aid"
    r3 = client.post("/search/semantic", json={"query": q3}).json()
    res3 = r3.get("results", [])
    t3_pass = False
    if len(res3) > 0:
        top_terms = [t.lower() for t in res3[0].get("highlight_terms", [])]
        expected_matches = ["scholarship", "financial", "assistance", "loan", "grants", "waiver"]
        t3_pass = any(any(exp in t for exp in expected_matches) for t in top_terms)
    print(f"  Query: \"{q3}\"")
    if res3:
        print(f"  Doc: {res3[0].get('image_name')} (Score: {res3[0].get('similarity_score', 0):.4f})")
        print(f"  Preview: \"{res3[0].get('preview_snippet')}\"")
        print(f"  Highlight Terms: {res3[0].get('highlight_terms')}")
        print(f"  Matched Concepts: {res3[0].get('matched_concepts')}")
    print(f"  Result: {'PASSED' if t3_pass else 'FAILED'}")
    if t3_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 4 — Natural Language Question Highlighting
    # -------------------------------------------------------------
    print("\n[TEST 4] Natural Language Question Highlighting")
    q4 = "where can students stay on campus?"
    r4 = client.post("/search/semantic", json={"query": q4}).json()
    res4 = r4.get("results", [])
    t4_pass = False
    if len(res4) > 0:
        top_terms = [t.lower() for t in res4[0].get("highlight_terms", [])]
        expected_matches = ["hostel", "resident", "residence", "room", "campus"]
        t4_pass = any(any(exp in t for exp in expected_matches) for t in top_terms)
    print(f"  Query: \"{q4}\"")
    if res4:
        print(f"  Doc: {res4[0].get('image_name')} (Score: {res4[0].get('similarity_score', 0):.4f})")
        print(f"  Preview: \"{res4[0].get('preview_snippet')}\"")
        print(f"  Highlight Terms: {res4[0].get('highlight_terms')}")
    print(f"  Result: {'PASSED' if t4_pass else 'FAILED'}")
    if t4_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 5 — Unrelated Query (No False Positives & Empty Highlights)
    # -------------------------------------------------------------
    print("\n[TEST 5] Unrelated Query (Zero Matches & Empty Highlights)")
    q5 = "Where can I find information about mango farming?"
    r5 = client.post("/search", json={"query": q5}).json()
    res5 = r5.get("results", [])
    t5_pass = (len(res5) == 0) and (r5.get("count") == 0)
    print(f"  Query: \"{q5}\"")
    print(f"  Matches Found: {len(res5)}")
    print(f"  Message: \"{r5.get('message')}\"")
    print(f"  Result: {'PASSED (0 False Positives)' if t5_pass else 'FAILED'}")
    if t5_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 6 — Multiple Results Document-Specific Highlight Isolation
    # -------------------------------------------------------------
    print("\n[TEST 6] Multiple Results Document-Specific Highlight Isolation")
    q6 = "campus accommodation"
    r6 = client.post("/search/semantic", json={"query": q6}).json()
    res6 = r6.get("results", [])
    t6_pass = False
    if len(res6) >= 2:
        doc1_terms = res6[0].get("highlight_terms", [])
        doc2_terms = res6[1].get("highlight_terms", [])
        doc1_name = res6[0].get("image_name")
        doc2_name = res6[1].get("image_name")
        # Ensure previews and highlights are extracted specifically from each document
        t6_pass = len(doc1_terms) > 0 and len(doc2_terms) > 0 and (res6[0].get("preview_snippet") != res6[1].get("preview_snippet"))
        print(f"  Doc #1 ({doc1_name}): Terms = {doc1_terms}")
        print(f"  Doc #2 ({doc2_name}): Terms = {doc2_terms}")
    print(f"  Result: {'PASSED' if t6_pass else 'FAILED'}")
    if t6_pass: passed_count += 1

    # -------------------------------------------------------------
    # Test 7 — Zero-Word-Overlap Paraphrased Query Highlighting
    # -------------------------------------------------------------
    print("\n[TEST 7] Zero-Word-Overlap Paraphrased Query")
    q7 = "How can I get money to continue my studies?"
    r7 = client.post("/search/semantic", json={"query": q7}).json()
    res7 = r7.get("results", [])
    t7_pass = False
    if len(res7) > 0:
        top_terms = [t.lower() for t in res7[0].get("highlight_terms", [])]
        expected_matches = ["scholarship", "loan", "financial", "grants", "waiver", "welfare"]
        t7_pass = any(any(exp in t for exp in expected_matches) for t in top_terms)
        # Ensure that non-existent query words are NOT fabricated into the highlight list
        query_words_not_in_doc = ["money", "continue", "studies"]
        doc_raw = res7[0].get("matched_text", "").lower()
        for qw in query_words_not_in_doc:
            if qw not in doc_raw:
                assert qw not in [t.lower() for t in top_terms], f"Query word '{qw}' should not be in highlight terms!"
    print(f"  Query: \"{q7}\"")
    if res7:
        print(f"  Doc: {res7[0].get('image_name')} (Score: {res7[0].get('similarity_score', 0):.4f})")
        print(f"  Preview: \"{res7[0].get('preview_snippet')}\"")
        print(f"  Highlight Terms: {res7[0].get('highlight_terms')}")
        print(f"  Matched Concepts: {res7[0].get('matched_concepts')}")
    print(f"  Result: {'PASSED' if t7_pass else 'FAILED'}")
    if t7_pass: passed_count += 1

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print(f"SUMMARY: {passed_count}/{total_tests} Tests Passed ({(passed_count/total_tests)*100:.1f}%)")
    print("=" * 90)
    return passed_count == total_tests


if __name__ == "__main__":
    test_suite()
