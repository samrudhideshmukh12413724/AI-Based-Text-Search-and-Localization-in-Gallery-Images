"""Metadata-Aware & Temporal Search Engine.

Enables queries combining semantic/keyword intent with temporal constraints:
- "fee receipt 2026"
- "exam documents from September"
- "admit card 2026-02-20"
- "hostel rules March 2026"
- "recent placement notice"

Parses temporal tokens, extracts target dates/years/months, and filters/boosts
documents matching file metadata and OCR entity dates.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional

from app import database
from app.entities.patterns import MONTH_MAP


# Temporal extraction patterns
YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")
DATE_PATTERN = re.compile(r"\b((?:19|20)\d\d[-/.](?:0?[1-9]|1[012])[-/.](?:0?[1-9]|[12][0-9]|3[01]))\b")
DATE_DMY_PATTERN = re.compile(r"\b((?:0?[1-9]|[12][0-9]|3[01])[-/.](?:0?[1-9]|1[012])[-/.](?:19|20)\d\d)\b")

MONTH_PATTERN = re.compile(
    r"\b(?:in|from|of|for|during)?\s*(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b",
    re.IGNORECASE,
)

RELATIVE_TERMS = {
    "recent": "recent",
    "latest": "recent",
    "newest": "recent",
    "last week": "last_week",
    "this week": "this_week",
    "this month": "this_month",
    "last month": "last_month",
    "today": "today",
    "yesterday": "yesterday",
}


def parse_temporal_query(query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parses temporal intent from a search query.

    Returns:
    (cleaned_text_query, temporal_filter_dict)
    """
    cleaned = query.strip()
    temporal_filter: Dict[str, Any] = {
        "is_temporal": False,
        "target_date": None,
        "target_year": None,
        "target_month": None,
        "relative": None,
    }

    # 1. Check for exact full date (YYYY-MM-DD or DD-MM-YYYY)
    m_date = DATE_PATTERN.search(cleaned)
    if m_date:
        raw_d = m_date.group(1).replace("/", "-").replace(".", "-")
        temporal_filter["target_date"] = raw_d
        temporal_filter["is_temporal"] = True
        cleaned = DATE_PATTERN.sub("", cleaned).strip()

    m_dmy = DATE_DMY_PATTERN.search(cleaned)
    if m_dmy and not temporal_filter["target_date"]:
        parts = re.split(r"[-/.]", m_dmy.group(1))
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            temporal_filter["target_date"] = f"{year:04d}-{month:02d}-{day:02d}"
            temporal_filter["is_temporal"] = True
            cleaned = DATE_DMY_PATTERN.sub("", cleaned).strip()

    # 2. Check for relative terms ("recent", "last week", etc.)
    q_lower = cleaned.lower()
    for phrase, rel_type in RELATIVE_TERMS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", q_lower):
            temporal_filter["relative"] = rel_type
            temporal_filter["is_temporal"] = True
            cleaned = re.sub(rf"\b{re.escape(phrase)}\b", "", cleaned, flags=re.IGNORECASE).strip()
            break

    # 3. Check for specific Month
    m_month = MONTH_PATTERN.search(cleaned)
    if m_month:
        month_str = m_month.group(1).lower()
        month_num = MONTH_MAP.get(month_str[:3])
        if month_num:
            temporal_filter["target_month"] = month_num
            temporal_filter["is_temporal"] = True
            # Clean only the matched span
            start, end = m_month.span()
            cleaned = (cleaned[:start] + cleaned[end:]).strip()

    # 4. Check for Year (e.g. 2026, 2025)
    m_year = YEAR_PATTERN.search(cleaned)
    if m_year:
        year_num = int(m_year.group(1))
        temporal_filter["target_year"] = year_num
        temporal_filter["is_temporal"] = True
        cleaned = YEAR_PATTERN.sub("", cleaned).strip()

    # Clean up any leftover punctuation or multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")

    return cleaned, temporal_filter


def match_temporal_criteria(doc: Dict[str, Any], temporal_filter: Dict[str, Any]) -> float:
    """
    Evaluates temporal compatibility between a document and the parsed filter.

    Returns:
    - 1.0 : Strong match (document date explicitly matches criteria)
    - 0.5 : Neutral (document has no date or weak match)
    - 0.0 : Contradiction (document explicitly has a different year/date)
    """
    if not temporal_filter.get("is_temporal"):
        return 1.0

    doc_date = doc.get("primary_date") or ""
    # Fallback to entities primary date or file modification date
    if not doc_date and doc.get("entities"):
        doc_date = doc["entities"].get("primary_date") or ""
    if not doc_date and doc.get("file_modified_at"):
        doc_date = doc["file_modified_at"][:10]

    # Check for all dates found in entities
    all_entity_dates = []
    if doc.get("entities") and doc["entities"].get("dates"):
        all_entity_dates = [d["iso"] for d in doc["entities"]["dates"]]

    target_date = temporal_filter.get("target_date")
    target_year = temporal_filter.get("target_year")
    target_month = temporal_filter.get("target_month")
    relative = temporal_filter.get("relative")

    # 1. Exact Date constraint
    if target_date:
        if doc_date == target_date or target_date in all_entity_dates:
            return 1.0
        if doc_date and doc_date != target_date:
            return 0.0
        return 0.3

    # 2. Year constraint (e.g. 2026)
    if target_year:
        year_str = str(target_year)
        if doc_date.startswith(year_str) or any(d.startswith(year_str) for d in all_entity_dates):
            # If month is also specified, verify month
            if target_month:
                month_str = f"{year_str}-{target_month:02d}"
                if doc_date.startswith(month_str) or any(d.startswith(month_str) for d in all_entity_dates):
                    return 1.0
                elif doc_date:
                    return 0.0
                return 0.3
            return 1.0
        elif doc_date:
            # Document explicitly has a date from a different year
            return 0.0
        return 0.4

    # 3. Month constraint without year
    if target_month:
        month_sub = f"-{target_month:02d}"
        if month_sub in doc_date or any(month_sub in d for d in all_entity_dates):
            return 1.0
        elif doc_date:
            return 0.0
        return 0.4

    # 4. Relative constraint (recent)
    if relative == "recent":
        if doc.get("file_modified_at") or doc.get("created_at"):
            return 0.9
        return 0.5

    return 0.5


def metadata_search(query: str, min_score: float = 0.65) -> Dict[str, Any]:
    """
    Executes unified search combining keyword/fuzzy text matching with metadata/temporal filters.
    """
    from app.search.ranking import unified_text_search

    cleaned_query, temporal_filter = parse_temporal_query(query)

    # If query had only temporal tokens (e.g. "2026" or "March 2026")
    effective_text_query = cleaned_query if cleaned_query else query

    text_res = unified_text_search(effective_text_query, min_score=min_score)
    candidates = text_res.get("results", [])

    if not temporal_filter.get("is_temporal"):
        return text_res

    # Apply temporal scoring and filtering
    enriched_results = []
    for item in candidates:
        img_id = item["id"]
        doc_row = database.get_image_by_id(img_id) or {}
        t_score = match_temporal_criteria(doc_row, temporal_filter)

        # If document contradicts the temporal filter, drop or heavily penalize
        if t_score == 0.0:
            continue

        kw_score = item["match_score"]
        # Temporal synergy: matching both text and temporal constraints boosts ranking
        fused_score = round(min(1.0, kw_score * 0.75 + t_score * 0.25 + (0.05 if t_score == 1.0 else 0.0)), 3)

        doc_date = doc_row.get("primary_date") or (doc_row.get("entities", {}).get("primary_date") if doc_row.get("entities") else None)
        item["match_score"] = fused_score
        item["temporal_match"] = t_score >= 0.8
        item["primary_date"] = doc_date
        enriched_results.append(item)

    enriched_results.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "query": query,
        "cleaned_query": cleaned_query,
        "temporal_filter": temporal_filter,
        "count": len(enriched_results),
        "results": enriched_results,
    }
