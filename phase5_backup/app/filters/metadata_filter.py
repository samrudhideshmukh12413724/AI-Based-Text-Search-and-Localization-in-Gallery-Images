"""Category and file format metadata filter module for Phase 4 Step 8.

Supports:
- Category matching: case-insensitive, trimmed, normalized (e.g. 'scholarship', 'SIGNATURE', 'general_device')
- Format matching: normalized image extension aliases ('jpg' == 'jpeg', 'png', 'webp')
"""

from pathlib import Path
from typing import List, Dict, Any, Set, Optional

FORMAT_ALIASES = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "webp": "webp",
}


def filter_by_category(rows: List[Dict[str, Any]], category: Optional[str]) -> Set[int]:
    """
    Filters rows by category name.
    Performs case-insensitive, whitespace-trimmed comparison.
    Supports both underscore and space variations (e.g. 'general device' matches 'GENERAL_DEVICE').
    """
    if not category or not category.strip():
        return {r["id"] for r in rows if "id" in r}

    cat_norm = category.strip().lower()
    cat_norm_alt = cat_norm.replace(" ", "_") if " " in cat_norm else cat_norm.replace("_", " ")

    matching_ids: Set[int] = set()
    for r in rows:
        row_id = r.get("id")
        if row_id is None:
            continue
        row_cat = (r.get("category") or "").strip().lower()
        if not row_cat:
            continue

        if row_cat == cat_norm or row_cat == cat_norm_alt:
            matching_ids.add(row_id)
        elif cat_norm in row_cat.split("_"):
            matching_ids.add(row_id)

    return matching_ids


def filter_by_format(rows: List[Dict[str, Any]], file_format: Optional[str]) -> Set[int]:
    """
    Filters rows by image file format.
    Normalizes format aliases (e.g. 'jpg' == 'jpeg').
    """
    if not file_format or not file_format.strip():
        return {r["id"] for r in rows if "id" in r}

    raw_fmt = file_format.strip().lower().lstrip(".")
    canonical_fmt = FORMAT_ALIASES.get(raw_fmt, raw_fmt)

    matching_ids: Set[int] = set()
    for r in rows:
        row_id = r.get("id")
        if row_id is None:
            continue

        # Check DB file_format column first
        db_fmt = (r.get("file_format") or "").strip().lower().lstrip(".")
        if db_fmt:
            norm_db_fmt = FORMAT_ALIASES.get(db_fmt, db_fmt)
            if norm_db_fmt == canonical_fmt:
                matching_ids.add(row_id)
                continue

        # Fallback to image_name / image_path suffix
        name = r.get("image_name") or r.get("image_path") or ""
        ext = Path(name).suffix.lower().lstrip(".")
        norm_ext = FORMAT_ALIASES.get(ext, ext)
        if norm_ext == canonical_fmt:
            matching_ids.add(row_id)

    return matching_ids
