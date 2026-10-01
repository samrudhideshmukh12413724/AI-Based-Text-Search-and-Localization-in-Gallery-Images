"""Ranking & Localization Refinement Module for Phase 4 Step 7A.

Implements deterministic grouping, source-aware relevance-first selection,
and explainable candidate formatting.
"""

from typing import List, Dict, Tuple, Any


GENERIC_SOURCES = {"full_doc", "card_proposal", "quadrant_anchor"}
SPECIFIC_SOURCES = {
    "color_region",
    "contour_graphic",
    "card_enclosure",
    "qr_detector",
    "fine_contour",
}


def rank_visual_candidates(
    doc_patches: Dict[int, List[Tuple[float, Dict[str, Any]]]],
    top_k: int = 10,
    query: str = "",
) -> List[Dict[str, Any]]:
    """
    Ranks visual document matches deterministically while preserving localization fidelity.

    Rules:
      1. Relevance First: The document ranking score is always the highest raw CLIP
         similarity across all its candidate patches, preserving overall retrieval power.
      2. Localization Refinement: When the top region is a generic fallback (full_doc,
         card_proposal, quadrant_anchor), prefer a detected specific visual region
         (color_region, contour_graphic, qr_detector, fine_contour) if its relevance
         score is within tolerance:
           - area >= 6%: delta <= 0.025
           - fine contour (< 6% area): delta <= 0.012 (protects full landscapes)
           - card_proposal / quadrant_anchor: delta <= 0.025
      3. Determinism: Stable sorting by similarity score descending, broken deterministically by ID.
    """
    if not doc_patches:
        return []

    doc_matches: List[Dict[str, Any]] = []

    for img_id, patches in doc_patches.items():
        if not patches:
            continue

        # Sort patches descending by similarity score, tie-breaking by region id/source
        patches.sort(key=lambda x: (x[0], x[1].get("id", 0)), reverse=True)
        doc_sim, top_r = patches[0]

        best_sim, best_r = doc_sim, top_r

        # Localization refinement when top region is generic
        if top_r.get("region_source") in GENERIC_SOURCES and len(patches) > 1:
            for sub_sim, sub_r in patches[1:]:
                if sub_r.get("region_source") in SPECIFIC_SOURCES:
                    if top_r.get("region_source") == "full_doc":
                        norm_bbox = sub_r.get("normalized_bbox", {})
                        norm_area = norm_bbox.get("width", 0.0) * norm_bbox.get("height", 0.0)
                        tolerance = 0.025 if norm_area >= 0.06 else 0.012
                    else:
                        tolerance = 0.025

                    if (doc_sim - sub_sim) <= tolerance:
                        best_sim, best_r = sub_sim, sub_r
                        break

        bbox_dict = best_r.get("bbox", {})
        norm_bbox_dict = best_r.get("normalized_bbox", {})
        loc_desc = best_r.get("location_desc", "Center")
        label_text = f"Visual Match: {loc_desc}"

        match_entry = {
            "id": img_id,
            "image_id": img_id,
            "image_name": best_r["image_name"],
            "image_path": best_r["image_path"],
            "extracted_text": best_r.get("extracted_text", ""),
            "category": best_r.get("category", ""),
            "similarity_score": round(doc_sim, 4),
            "best_region": {
                "source": best_r.get("region_source", "visual_region"),
                "location_desc": loc_desc,
                "bbox": bbox_dict,
                "normalized_bbox": norm_bbox_dict,
                "confidence": round(best_sim, 4),
                "label": label_text,
            },
            # Explainability fields
            "query": query,
            "location_desc": loc_desc,
            "bbox": bbox_dict,
            "normalized_bbox": norm_bbox_dict,
            "confidence": round(best_sim, 4),
            "label": label_text,
        }
        doc_matches.append(match_entry)

    # Sort descending by score; break ties by image_id ascending for 100% determinism
    doc_matches.sort(key=lambda x: (-x["similarity_score"], x["id"]))

    return doc_matches[:top_k]
