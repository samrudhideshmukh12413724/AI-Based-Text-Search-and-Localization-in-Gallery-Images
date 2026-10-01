"""Date and temporal candidate filter module for Phase 4 Step 8.

Supports:
- Inclusive date range filtering (date_from, date_to in ISO format: YYYY-MM-DD or YYYY-MM or YYYY)
- Year filtering (exact 4-digit calendar year)
"""

from typing import List, Dict, Any, Set, Optional


def _extract_all_row_dates(row: Dict[str, Any]) -> List[str]:
    """
    Extracts all candidate dates associated with a document:
    1. primary_date from metadata
    2. entities_json dates and primary_date
    3. file_modified_at fallback
    """
    dates: List[str] = []

    # 1. Primary date column
    pd = (row.get("primary_date") or "").strip()
    if pd:
        dates.append(pd)

    # 2. Structured entity dates
    entities = row.get("entities")
    if isinstance(entities, dict):
        epd = (entities.get("primary_date") or "").strip()
        if epd and epd not in dates:
            dates.append(epd)
        for d in entities.get("dates", []):
            if isinstance(d, dict) and d.get("iso"):
                iso = str(d["iso"]).strip()
                if iso and iso not in dates:
                    dates.append(iso)

    # 3. File modified timestamp fallback (first 10 chars YYYY-MM-DD)
    if not dates:
        mod = (row.get("file_modified_at") or "").strip()
        if mod:
            iso_mod = mod[:10]
            if iso_mod:
                dates.append(iso_mod)

    return dates


def _date_ge(d: str, d_from: str) -> bool:
    """Returns True if document date d >= d_from."""
    len_d, len_from = len(d), len(d_from)
    if len_d == 4 and len_from > 4:
        return d >= d_from[:4]
    if len_d > 4 and len_from == 4:
        return d[:4] >= d_from
    if len_d == 7 and len_from > 7:
        return d >= d_from[:7]
    if len_d > 7 and len_from == 7:
        return d[:7] >= d_from
    return d >= d_from


def _date_le(d: str, d_to: str) -> bool:
    """Returns True if document date d <= d_to."""
    len_d, len_to = len(d), len(d_to)
    if len_d == 4 and len_to > 4:
        return d <= d_to[:4]
    if len_d > 4 and len_to == 4:
        return d[:4] <= d_to
    if len_d == 7 and len_to > 7:
        return d <= d_to[:7]
    if len_d > 7 and len_to == 7:
        return d[:7] <= d_to
    return d <= d_to


def filter_by_date_range(
    rows: List[Dict[str, Any]],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Set[int]:
    """
    Filters rows by an inclusive date range [date_from, date_to].
    If a document has at least one candidate date within the range, its ID is included.
    Documents without any dates do not match.
    """
    clean_from = date_from.strip() if date_from and date_from.strip() else None
    clean_to = date_to.strip() if date_to and date_to.strip() else None

    if not clean_from and not clean_to:
        return {r["id"] for r in rows if "id" in r}

    matching_ids: Set[int] = set()
    for r in rows:
        row_id = r.get("id")
        if row_id is None:
            continue
        row_dates = _extract_all_row_dates(r)
        if not row_dates:
            continue

        for d in row_dates:
            satisfies_from = (clean_from is None) or _date_ge(d, clean_from)
            satisfies_to = (clean_to is None) or _date_le(d, clean_to)
            if satisfies_from and satisfies_to:
                matching_ids.add(row_id)
                break

    return matching_ids


def filter_by_year(rows: List[Dict[str, Any]], year: Optional[int]) -> Set[int]:
    """
    Filters rows by exact calendar year.
    Matches documents whose primary date or entity dates begin with or equal str(year).
    """
    if year is None:
        return {r["id"] for r in rows if "id" in r}

    year_str = str(year).strip()
    matching_ids: Set[int] = set()
    for r in rows:
        row_id = r.get("id")
        if row_id is None:
            continue
        row_dates = _extract_all_row_dates(r)
        if any(d.startswith(year_str) or d[:4] == year_str for d in row_dates):
            matching_ids.add(row_id)

    return matching_ids
