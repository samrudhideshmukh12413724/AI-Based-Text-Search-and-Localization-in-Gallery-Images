"""Real-Time Duplicate & Near-Duplicate Detector.

Detects exact binary matches (SHA-256) and visual near-duplicates (pHash)
for an incoming image against indexed database images.

Classification hierarchy:
1. Exact Binary (SHA-256 match) -> exact_binary, distance=0, sim=1.0
2. Exact Visual (pHash match) -> exact_phash, distance=0, sim=1.0
3. Near Duplicate (Hamming dist 1..5) -> near_duplicate, distance=dist, sim=1-dist/64
4. Distinct Image (Hamming dist > 5) -> unique
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union
import sqlite3

from app import database
from app.duplicates.hasher import (
    compute_sha256,
    compute_phash,
    hamming_distance,
    phash_similarity,
)


def check_duplicate(
    image_path: Union[str, Path],
    exclude_image_id: Optional[int] = None,
    max_hamming_distance: int = 5,
) -> Dict[str, Any]:
    """
    Evaluates an incoming image against indexed images to detect duplicates.

    Returns:
    {
        "is_duplicate": bool,
        "match_type": "exact_binary" | "exact_phash" | "near_duplicate" | "unique" | "invalid_image",
        "canonical_id": Optional[int],
        "canonical_image_name": Optional[str],
        "hamming_distance": int,
        "similarity": float,
        "sha256_hash": str,
        "phash": str
    }
    """
    path = Path(image_path)
    if not path.is_file():
        return {
            "is_duplicate": False,
            "match_type": "invalid_image",
            "canonical_id": None,
            "canonical_image_name": None,
            "hamming_distance": 64,
            "similarity": 0.0,
            "sha256_hash": "",
            "phash": "",
        }

    sha256_val = compute_sha256(path)
    phash_val = compute_phash(path)

    if not sha256_val or not phash_val:
        return {
            "is_duplicate": False,
            "match_type": "invalid_image",
            "canonical_id": None,
            "canonical_image_name": None,
            "hamming_distance": 64,
            "similarity": 0.0,
            "sha256_hash": sha256_val,
            "phash": phash_val,
        }

    ex_id = exclude_image_id if exclude_image_id is not None else -1

    with database._connect() as conn:
        # 1. Check exact binary match (SHA-256)
        row_sha = conn.execute(
            """
            SELECT id, image_name, image_path, sha256_hash, phash, canonical_image_id, is_duplicate
            FROM images
            WHERE sha256_hash = ? AND id != ?
            LIMIT 1
            """,
            (sha256_val, ex_id),
        ).fetchone()

        if row_sha:
            canonical_id = row_sha["canonical_image_id"] if row_sha["canonical_image_id"] else row_sha["id"]
            return {
                "is_duplicate": True,
                "match_type": "exact_binary",
                "canonical_id": canonical_id,
                "canonical_image_name": row_sha["image_name"],
                "hamming_distance": 0,
                "similarity": 1.0,
                "sha256_hash": sha256_val,
                "phash": phash_val,
            }

        # 2. Check exact perceptual match (pHash dist = 0 via SQL index)
        row_phash = conn.execute(
            """
            SELECT id, image_name, image_path, sha256_hash, phash, canonical_image_id, is_duplicate
            FROM images
            WHERE phash = ? AND id != ?
            LIMIT 1
            """,
            (phash_val, ex_id),
        ).fetchone()

        if row_phash:
            canonical_id = row_phash["canonical_image_id"] if row_phash["canonical_image_id"] else row_phash["id"]
            return {
                "is_duplicate": True,
                "match_type": "exact_phash",
                "canonical_id": canonical_id,
                "canonical_image_name": row_phash["image_name"],
                "hamming_distance": 0,
                "similarity": 1.0,
                "sha256_hash": sha256_val,
                "phash": phash_val,
            }

        # 3. Near-duplicate scan across indexed pHashes in Python
        candidates = conn.execute(
            """
            SELECT id, image_name, image_path, phash, canonical_image_id, is_duplicate
            FROM images
            WHERE phash IS NOT NULL AND phash != '' AND id != ?
            """,
            (ex_id,),
        ).fetchall()

    best_dist = 64
    best_candidate = None

    for c in candidates:
        cand_phash = c["phash"]
        dist = hamming_distance(phash_val, cand_phash)
        if dist < best_dist:
            best_dist = dist
            best_candidate = c
            if best_dist == 0:
                break

    if best_candidate and best_dist <= max_hamming_distance:
        canonical_id = (
            best_candidate["canonical_image_id"]
            if best_candidate["canonical_image_id"]
            else best_candidate["id"]
        )
        sim = phash_similarity(phash_val, best_candidate["phash"])
        match_type = "exact_phash" if best_dist == 0 else "near_duplicate"
        return {
            "is_duplicate": True,
            "match_type": match_type,
            "canonical_id": canonical_id,
            "canonical_image_name": best_candidate["image_name"],
            "hamming_distance": best_dist,
            "similarity": sim,
            "sha256_hash": sha256_val,
            "phash": phash_val,
        }

    # Unique / Distinct
    lowest_sim = phash_similarity(phash_val, best_candidate["phash"]) if best_candidate else 0.0
    return {
        "is_duplicate": False,
        "match_type": "unique",
        "canonical_id": None,
        "canonical_image_name": None,
        "hamming_distance": best_dist,
        "similarity": lowest_sim,
        "sha256_hash": sha256_val,
        "phash": phash_val,
    }
