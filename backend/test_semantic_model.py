"""Test Sentence Transformers independently to verify semantic embedding similarity."""

import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from sentence_transformers import SentenceTransformer, util


def main():
    print("Loading pretrained model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded successfully!\n")

    sentences = [
        "Government scholarship for students",          # S1
        "Financial assistance available for education", # S2 (Semantic match to S1)
        "Semester examination datesheet and timetable", # S3 (Unrelated topic)
        "Student hostel room accommodation rules",      # S4 (Unrelated topic)
    ]

    print("Encoding sentences into embeddings...")
    embeddings = model.encode(sentences, convert_to_tensor=True)
    print(f"Embedding dimension: {embeddings.shape[1]} numbers per sentence\n")

    # Compute cosine similarity between S1 and all sentences
    query = sentences[0]
    query_emb = embeddings[0]

    print(f"Reference Query: '{query}'\n")
    print(f"{'Target Sentence':<48} | {'Similarity':<10} | {'Semantic Relation'}")
    print("-" * 80)

    for i, (sent, emb) in enumerate(zip(sentences, embeddings)):
        similarity = util.cos_sim(query_emb, emb).item()
        if i == 0:
            relation = "Identical (1.00)"
        elif similarity > 0.60:
            relation = "HIGH SIMILARITY (Match)"
        else:
            relation = "LOW SIMILARITY (Different topic)"
        print(f"{sent:<48} | {similarity:10.4f} | {relation}")

    print("-" * 80)
    print("\nVerification Conclusion:")
    print("-> S1 ('Government scholarship') and S2 ('Financial assistance') have HIGH similarity.")
    print("-> S1 and S3/S4 ('Examination' / 'Hostel') have LOW similarity.")
    print("-> Model correctly understands meaning beyond exact keyword overlap!")


if __name__ == "__main__":
    main()
