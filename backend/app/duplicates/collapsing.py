"""Search Results Duplicate Collapsing Module.

Collapses duplicate variants in search results under their canonical image.
Preserves existing search response fields, ranking order, and scores.
"""

from typing import Any, Dict, List
from app import database


def collapse_duplicate_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Collapses duplicate variants under their canonical image.

    Rules:
    1. If multiple results in search results belong to the same canonical group,
       collapse them into a single representative result.
    2. The canonical image represents the group. If the canonical image itself is in
       the results, it takes the highest similarity score achieved by any variant in its group.
    3. If only duplicate variants appear in the results for that group, the highest-ranked
       variant is represented by its canonical image.
    4. Non-canonical duplicate variants are removed from top-level results and attached
       to the representative under `duplicate_variants`.
    5. If an image has no other copies in the search results:
       - If it is already canonical, it remains as-is.
       - If it is a duplicate variant:
         - If it is an exact copy (exact_binary or exact_phash) of its canonical,
           it is represented by its canonical image.
         - Otherwise (near-duplicate with distinct content), it remains as-is.
    6. Additive metadata added to every result:
       - `is_duplicate`: bool
       - `canonical_image_id`: Optional[int]
       - `canonical_image_name`: Optional[str]
       - `duplicate_count`: int (number of collapsed variants in these search results)
       - `duplicate_variants`: List[Dict] (metadata of collapsed variants)
       - `has_duplicates`: bool
    """
    if not results:
        return []

    # 1. Fetch DB metadata for all result image IDs
    db_cache: Dict[int, Dict[str, Any]] = {}
    for item in results:
        img_id = item.get("id")
        if img_id is not None and img_id not in db_cache:
            row = database.get_image_by_id(img_id)
            if row:
                db_cache[img_id] = row

    # 2. Map each item to its canonical group ID
    def get_canon_id(item: Dict[str, Any]) -> int:
        img_id = item.get("id")
        row = db_cache.get(img_id)
        if row and row.get("is_duplicate") and row.get("canonical_image_id"):
            return row["canonical_image_id"]
        return img_id

    # 3. Group results by canonical group ID while preserving appearance order
    groups: Dict[int, List[Dict[str, Any]]] = {}
    group_order: List[int] = []

    for item in results:
        cid = get_canon_id(item)
        if cid not in groups:
            groups[cid] = []
            group_order.append(cid)
        groups[cid].append(item)

    # 4. Form collapsed representative cards
    collapsed: List[Dict[str, Any]] = []

    for cid in group_order:
        group_items = groups[cid]

        # Best (highest-scoring) item in this group
        best_item = max(group_items, key=lambda x: float(x.get("similarity_score", 0.0)))
        best_score = best_item.get("similarity_score", 0.0)

        # Check if the canonical image itself is among the group items
        canon_item = next((it for it in group_items if it.get("id") == cid), None)

        # Fetch canonical row from DB if needed
        if cid not in db_cache:
            c_row = database.get_image_by_id(cid)
            if c_row:
                db_cache[cid] = c_row
        canon_row = db_cache.get(cid)

        # Determine representative card
        if canon_item is not None:
            # Canonical image is present in results: it is the representative, boosted to best score
            rep = dict(canon_item)
            rep["similarity_score"] = best_score
            if best_item.get("search_type") == "multimodal":
                rep["search_type"] = "multimodal"
            # Variants are all OTHER items in this group
            variants = [it for it in group_items if it.get("id") != cid]
        elif len(group_items) > 1:
            # Multiple duplicate copies matched, but canonical was not returned
            single_item = best_item
            s_id = single_item.get("id")
            s_row = db_cache.get(s_id)
            mtype = s_row.get("duplicate_match_type", "") if s_row else ""
            if mtype in ("exact_binary", "exact_phash") and canon_row:
                rep = dict(single_item)
                rep["id"] = canon_row["id"]
                rep["image_name"] = canon_row["image_name"]
                rep["image_path"] = canon_row["image_path"]
                rep["image_url"] = f"/uploads/{canon_row['image_name']}"
                variants = [dict(it) for it in group_items]
            else:
                rep = dict(best_item)
                variants = [it for it in group_items if it.get("id") != best_item.get("id")]
        else:
            # Exactly 1 item in group
            single_item = group_items[0]
            s_id = single_item.get("id")
            s_row = db_cache.get(s_id)
            mtype = s_row.get("duplicate_match_type", "") if s_row else ""

            if s_id != cid and mtype in ("exact_binary", "exact_phash") and canon_row:
                # Exact duplicate copy represented by canonical image
                rep = dict(single_item)
                rep["id"] = canon_row["id"]
                rep["image_name"] = canon_row["image_name"]
                rep["image_path"] = canon_row["image_path"]
                rep["image_url"] = f"/uploads/{canon_row['image_name']}"
                variants = [dict(single_item)]
            else:
                # Canonical or single distinct item
                rep = dict(single_item)
                variants = []

        # Format variant objects for response
        formatted_variants = []
        for v in variants:
            v_row = db_cache.get(v.get("id"))
            formatted_variants.append({
                "id": v.get("id"),
                "image_name": v.get("image_name"),
                "image_path": v.get("image_path", ""),
                "image_url": v.get("image_url", f"/uploads/{v.get('image_name', '')}"),
                "similarity_score": v.get("similarity_score", 0.0),
                "search_type": v.get("search_type", "keyword"),
                "duplicate_match_type": (
                    v_row.get("duplicate_match_type", "near_duplicate")
                    if v_row
                    else "near_duplicate"
                ),
                "duplicate_similarity": (
                    v_row.get("duplicate_similarity", 1.0) if v_row else 1.0
                ),
            })

        rep["is_duplicate"] = False
        rep["canonical_image_id"] = cid if rep.get("id") != cid else None
        rep["canonical_image_name"] = canon_row.get("image_name") if canon_row else None
        rep["duplicate_count"] = len(formatted_variants)
        rep["duplicate_variants"] = formatted_variants
        rep["has_duplicates"] = len(formatted_variants) > 0

        collapsed.append(rep)

    # Re-sort collapsed list to ensure perfect score/modality ranking order
    collapsed.sort(
        key=lambda x: (
            x.get("similarity_score", 0.0),
            1.0 if x.get("search_type") == "multimodal"
            else (0.5 if x.get("search_type") == "visual" else 0.0)
        ),
        reverse=True,
    )

    return collapsed
