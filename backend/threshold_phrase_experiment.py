"""Empirical experiment to determine the optimal phrase-level similarity threshold."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"

import numpy as np
from sentence_transformers import SentenceTransformer
from app.semantic_search import get_embedding_model

test_cases = [
    {
        "query": "financial aid",
        "text": "Government Scholarship Application 2026 Financial assistance and education loan support for eligible college students.",
        "expected_phrases": ["scholarship", "financial assistance", "education loan"],
        "unrelated_words": ["government", "application", "college", "eligible", "students", "2026"],
    },
    {
        "query": "where can students stay on campus?",
        "text": "Hostel Room Allocation Campus residence form and student resident guidelines curfew timings.",
        "expected_phrases": ["hostel room allocation", "campus residence", "student resident guidelines"],
        "unrelated_words": ["form", "timings", "curfew", "guidelines"],
    },
    {
        "query": "How can I get money to continue my studies?",
        "text": "Merit Student Scholarship National welfare scheme offering fee waiver and financial grants.",
        "expected_phrases": ["scholarship", "fee waiver", "financial grants", "welfare scheme"],
        "unrelated_words": ["student", "national", "offering", "scheme"],
    },
]


def extract_candidate_ngrams(text: str, max_n=3) -> list[str]:
    import re
    stopwords = {"the", "a", "an", "and", "or", "for", "in", "on", "at", "to", "from", "of", "with", "is", "was", "are", "were", "by", "as", "about", "can", "and"}
    words = [w.strip() for w in re.split(r"[\s,.;:!?\(\)\/]+", text) if w.strip()]
    
    candidates = []
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            ngram = words[i:i+n]
            # Skip if start or end is a stopword or if all are stopwords
            if ngram[0].lower() in stopwords or ngram[-1].lower() in stopwords:
                continue
            phrase = " ".join(ngram)
            if len(phrase) >= 3 and not phrase.isdigit():
                candidates.append(phrase)
    return list(dict.fromkeys(candidates))


def run_experiment():
    model = get_embedding_model()
    print("=" * 85)
    print("      EMPIRICAL PHRASE-LEVEL THRESHOLD SIMILARITY EXPERIMENT")
    print("=" * 85)

    all_scores = []
    threshold_tests = [0.30, 0.35, 0.38, 0.40, 0.45]

    for tc in test_cases:
        query = tc["query"]
        text = tc["text"]
        q_emb = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)

        candidates = extract_candidate_ngrams(text, max_n=3)
        c_embs = model.encode(candidates, convert_to_numpy=True, normalize_embeddings=True)
        scores = np.dot(c_embs, q_emb)

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        print(f"\n[Query]: \"{query}\"")
        print(f"[Document Text]: \"{text}\"")
        print(f"{'Candidate Phrase':<35} | {'Cosine Similarity':<18} | {'Type'}")
        print("-" * 75)
        for phrase, score in ranked[:10]:
            p_lower = phrase.lower()
            is_relevant = any(exp in p_lower or p_lower in exp for exp in tc["expected_phrases"])
            label = "TARGET RELEVANT" if is_relevant else "Generic / Filler"
            print(f"{phrase:<35} | {score:8.4f}          | {label}")
            all_scores.append((label, score))

    print("\n" + "=" * 85)
    print("THRESHOLD BEHAVIOR COMPARISON:")
    print("-" * 85)
    for tau in threshold_tests:
        relevant_kept = sum(1 for label, s in all_scores if label == "TARGET RELEVANT" and s >= tau)
        relevant_total = sum(1 for label, s in all_scores if label == "TARGET RELEVANT")
        filler_rejected = sum(1 for label, s in all_scores if label == "Generic / Filler" and s < tau)
        filler_total = sum(1 for label, s in all_scores if label == "Generic / Filler")
        
        rel_rate = (relevant_kept / relevant_total * 100) if relevant_total else 0
        rej_rate = (filler_rejected / filler_total * 100) if filler_total else 0
        print(f"Threshold tau = {tau:.2f} -> Relevant Phrase Recall: {rel_rate:5.1f}% | Noise Rejection: {rej_rate:5.1f}%")
    print("=" * 85)


if __name__ == "__main__":
    run_experiment()
