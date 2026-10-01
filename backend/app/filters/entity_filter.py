"""Entity type candidate filter module for Phase 4 Step 8.

Supports filtering by verified structured entities extracted from OCR text:
- 'aadhaar' / 'aadhaar_number': Aadhaar 12-digit UID
- 'pan' / 'pan_number': PAN card format
- 'phone' / 'phone_number': Phone numbers
- 'email': Email addresses
- 'url': Web URLs
- 'amount' / 'money': Currency amounts
- 'id' / 'ids' / 'application_id': Generic alphanumeric IDs
- 'date' / 'dates': Document date entities
"""

from typing import List, Dict, Any, Set, Optional

ENTITY_KEY_MAP = {
    "aadhaar": ["aadhaar_numbers"],
    "aadhaar_number": ["aadhaar_numbers"],
    "pan": ["pan_numbers"],
    "pan_number": ["pan_numbers"],
    "phone": ["phone_numbers"],
    "phone_number": ["phone_numbers"],
    "email": ["emails"],
    "url": ["urls"],
    "amount": ["amounts"],
    "money": ["amounts"],
    "id": ["ids"],
    "ids": ["ids"],
    "application_id": ["ids"],
    "date": ["dates"],
    "dates": ["dates"],
}


def filter_by_entity_type(rows: List[Dict[str, Any]], entity_type: Optional[str]) -> Set[int]:
    """
    Filters rows by the presence of a non-empty entity field in entities_json.
    """
    if not entity_type or not entity_type.strip():
        return {r["id"] for r in rows if "id" in r}

    norm = entity_type.strip().lower()
    target_keys = ENTITY_KEY_MAP.get(norm, [norm])

    matching_ids: Set[int] = set()
    for r in rows:
        row_id = r.get("id")
        if row_id is None:
            continue

        entities = r.get("entities")
        if isinstance(entities, dict):
            matched = False
            for k in target_keys:
                val = entities.get(k)
                if val:
                    matching_ids.add(row_id)
                    matched = True
                    break
            if matched:
                continue

            if norm in ("date", "dates") and (r.get("primary_date") or entities.get("primary_date")):
                matching_ids.add(row_id)

    return matching_ids
