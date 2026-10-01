"""Corpus-Wide Duplicate & Near-Duplicate Grouping Module.

Processes the indexed image corpus to discover and establish duplicate clusters:
1. Computes / reads SHA-256 bit-for-bit checksums and 64-bit perceptual hashes (pHash).
2. Finds exact binary matches (SHA-256 match -> exact_binary).
3. Finds exact perceptual matches (pHash match -> exact_phash).
4. Finds near-duplicates within operational Hamming distance 1..5 (near_duplicate).
5. Chooses canonical image: Deterministic rule = earliest existing image ID (min ID) in cluster.
6. Links duplicate variants -> canonical_image_id with calculated similarity score.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app import database
from app.duplicates.hasher import (
    compute_sha256,
    compute_phash,
    hamming_distance,
    phash_similarity,
)



def group_corpus(
    persist: bool = True,
    max_hamming_distance: int = 5,
) -> Dict[str, Any]:
    """
    Groups the entire image corpus into canonical images and duplicate variants.

    Deterministic Rule:
    The earliest existing image ID (lowest ID) in any duplicate group becomes canonical.

    Canonical image fields:
        is_duplicate = 0
        canonical_image_id = None (NULL in DB)
        duplicate_similarity = 0.0
        duplicate_match_type = "unique"

    Duplicate variant fields:
        is_duplicate = 1
        canonical_image_id = <canonical ID>
        duplicate_similarity = <score 0.0 .. 1.0>
        duplicate_match_type = "exact_binary" | "exact_phash" | "near_duplicate"
    """
    raw_images = database.list_images()
    sorted_images = sorted(raw_images, key=lambda x: x["id"])

    errors: List[str] = []
    data: List[Dict[str, Any]] = []

    # Step 1: Read / compute SHA-256 + pHash
    for img in sorted_images:
        path = Path(img["image_path"])
        if not path.is_file():
            errors.append(f"Image ID {img['id']} file not found: {img['image_path']}")
            continue

        sha_val = img.get("sha256_hash") or ""
        phash_val = img.get("phash") or ""

        if len(sha_val) != 64:
            sha_val = compute_sha256(path)
        if len(phash_val) != 16:
            phash_val = compute_phash(path)


        if not sha_val or not phash_val:
            errors.append(f"Failed to compute hashes for image ID {img['id']}: {img['image_name']}")
            continue

        data.append({
            "id": img["id"],
            "image_name": img["image_name"],
            "image_path": str(path),
            "sha256_hash": sha_val,
            "phash": phash_val,
        })

    # Disjoint-set / union-find tracking
    parent: Dict[int, int] = {d["id"]: d["id"] for d in data}

    def find_root(x: int) -> int:
        if parent[x] != x:
            parent[x] = find_root(parent[x])
        return parent[x]

    def union_roots(a: int, b: int) -> None:
        root_a = find_root(a)
        root_b = find_root(b)
        if root_a != root_b:
            if root_a < root_b:
                parent[root_b] = root_a
            else:
                parent[root_a] = root_b

    # Step 2: Find exact binary matches (SHA-256)
    sha_map: Dict[str, List[Dict[str, Any]]] = {}
    for d in data:
        sha_map.setdefault(d["sha256_hash"], []).append(d)

    for sha, group in sha_map.items():
        if len(group) > 1:
            first_id = group[0]["id"]
            for member in group[1:]:
                union_roots(first_id, member["id"])

    # Step 3: Find exact pHash matches (pHash dist = 0)
    cluster_reps_s2 = [d for d in data if find_root(d["id"]) == d["id"]]
    phash_map: Dict[str, List[Dict[str, Any]]] = {}
    for d in cluster_reps_s2:
        phash_map.setdefault(d["phash"], []).append(d)

    for ph, group in phash_map.items():
        if len(group) > 1:
            first_id = group[0]["id"]
            for member in group[1:]:
                union_roots(first_id, member["id"])

    # Step 4: Find near-duplicates (distance 1..max_hamming_distance)
    # Compare remaining cluster representatives against established canonicals
    # in ID order to enforce distance <= max_hamming_distance directly from canonical.
    cluster_reps_s3 = sorted(
        [d for d in data if find_root(d["id"]) == d["id"]],
        key=lambda x: x["id"],
    )

    final_canonicals: List[Dict[str, Any]] = []
    for rep in cluster_reps_s3:
        best_cand = None
        best_dist = 64

        for c in final_canonicals:
            dist = hamming_distance(rep["phash"], c["phash"])
            if dist < best_dist:
                best_dist = dist
                best_cand = c

        if best_cand is not None and 1 <= best_dist <= max_hamming_distance:
            # Link to the established canonical root
            union_roots(best_cand["id"], rep["id"])
        else:
            final_canonicals.append(rep)

    # Flatten all parent pointers to absolute canonical roots
    for d in data:
        find_root(d["id"])


    # Step 5 & 6: Choose canonical images and link variants
    img_by_id = {d["id"]: d for d in data}
    groups: Dict[int, Dict[str, Any]] = {}
    for d in data:
        cid = parent[d["id"]]
        if cid not in groups:
            groups[cid] = {
                "canonical": img_by_id[cid],
                "variants": [],
            }
        if d["id"] != cid:
            groups[cid]["variants"].append(d)

    # Classify relationships and update DB
    unique_canonical_count = 0
    duplicate_count = 0
    exact_binary_count = 0
    exact_phash_count = 0
    near_duplicate_count = 0

    records_to_persist: List[Dict[str, Any]] = []

    for d in data:
        img_id = d["id"]
        canon_id = parent[img_id]
        canon = img_by_id[canon_id]

        if img_id == canon_id:
            # Canonical image
            unique_canonical_count += 1
            rec = {
                "id": img_id,
                "image_name": d["image_name"],
                "sha256_hash": d["sha256_hash"],
                "phash": d["phash"],
                "is_duplicate": 0,
                "canonical_image_id": None,
                "duplicate_similarity": 0.0,
                "duplicate_match_type": "unique",
            }
        else:
            # Duplicate variant
            duplicate_count += 1
            if d["sha256_hash"] == canon["sha256_hash"]:
                match_type = "exact_binary"
                sim = 1.0
                exact_binary_count += 1
            elif d["phash"] == canon["phash"]:
                match_type = "exact_phash"
                sim = 1.0
                exact_phash_count += 1
            else:
                match_type = "near_duplicate"
                sim = phash_similarity(d["phash"], canon["phash"])
                near_duplicate_count += 1

            rec = {
                "id": img_id,
                "image_name": d["image_name"],
                "sha256_hash": d["sha256_hash"],
                "phash": d["phash"],
                "is_duplicate": 1,
                "canonical_image_id": canon_id,
                "duplicate_similarity": sim,
                "duplicate_match_type": match_type,
            }

        records_to_persist.append(rec)

    # Persist to database if requested
    if persist:
        for r in records_to_persist:
            database.update_image_duplicates(
                image_id=r["id"],
                sha256_hash=r["sha256_hash"],
                phash=r["phash"],
                is_duplicate=r["is_duplicate"],
                canonical_image_id=r["canonical_image_id"],
                duplicate_similarity=r["duplicate_similarity"],
                duplicate_match_type=r["duplicate_match_type"],
            )

    # Calculate group statistics
    duplicate_groups = {k: v for k, v in groups.items() if len(v["variants"]) > 0}
    largest_group_info: Dict[str, Any] = {}
    if duplicate_groups:
        sorted_groups = sorted(
            duplicate_groups.values(),
            key=lambda g: len(g["variants"]),
            reverse=True,
        )
        largest = sorted_groups[0]
        c = largest["canonical"]
        largest_group_info = {
            "canonical_id": c["id"],
            "canonical_name": c["image_name"],
            "variant_count": len(largest["variants"]),
            "total_group_size": len(largest["variants"]) + 1,
            "sample_variants": [
                {"id": v["id"], "name": v["image_name"]}
                for v in largest["variants"][:5]
            ],
        }

    return {
        "total_images_processed": len(data),
        "unique_canonical_images": unique_canonical_count,
        "duplicate_images": duplicate_count,
        "duplicate_groups_count": len(duplicate_groups),
        "exact_binary_matches": exact_binary_count,
        "exact_phash_matches": exact_phash_count,
        "near_duplicates": near_duplicate_count,
        "largest_duplicate_group": largest_group_info,
        "errors": errors,
    }


def main():
    """CLI runner to execute grouping against corpus and report statistics."""
    print("=" * 80)
    print("PHASE 4 STEP 5C-3: CORPUS DUPLICATE GROUPING")
    print("=" * 80)

    result = group_corpus(persist=True)

    print(f"Total images processed : {result['total_images_processed']}")
    print(f"Unique/canonical images: {result['unique_canonical_images']}")
    print(f"Duplicate images       : {result['duplicate_images']}")
    print(f"Duplicate groups count : {result['duplicate_groups_count']}")
    print(f"Exact binary matches   : {result['exact_binary_matches']}")
    print(f"Exact pHash matches    : {result['exact_phash_matches']}")
    print(f"Near-duplicates        : {result['near_duplicates']}")

    largest = result["largest_duplicate_group"]
    if largest:
        print(
            f"Largest duplicate group: Canonical ID {largest['canonical_id']} "
            f"({largest['canonical_name']}) with {largest['variant_count']} variants "
            f"(Total group size: {largest['total_group_size']})"
        )
        print("Sample variants:")
        for s in largest["sample_variants"]:
            print(f"  - ID {s['id']}: {s['name']}")

    print(f"Errors encountered     : {len(result['errors'])}")
    for err in result["errors"]:
        print(f"  [ERROR] {err}")

    print("=" * 80)
    print("STEP 5C-3 DUPLICATE GROUPING COMPLETED SUCCESSFULLY [OK]")
    print("=" * 80)


if __name__ == "__main__":
    main()
