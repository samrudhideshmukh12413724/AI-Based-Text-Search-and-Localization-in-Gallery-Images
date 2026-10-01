"""High-level document entity extraction engine.

Aggregates specialized pattern extractors into a unified, structured entity
schema suitable for database persistence, metadata filtering, and semantic enrichment.
"""

from typing import Dict, Any, List, Optional
from app.entities.patterns import (
    extract_dates,
    extract_emails,
    extract_phone_numbers,
    extract_urls,
    extract_amounts,
    extract_ids,
    extract_aadhaar,
    extract_pan,
)


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Extracts all structured document entities from raw or preprocessed OCR text.

    Returns a structured dictionary:
    {
        "dates": [{"raw": "...", "iso": "YYYY-MM-DD", "precision": "day"}],
        "emails": ["student@example.com"],
        "phone_numbers": ["9876543210"],
        "urls": ["https://apex.edu"],
        "amounts": [{"raw": "₹25,000", "value": 25000.0, "currency": "INR"}],
        "ids": [{"type": "Roll Number", "value": "23AIML123"}],
        "aadhaar_numbers": ["4829 1048 9301"],
        "pan_numbers": ["ABCDE1234F"],
        "total_entities": int,
        "has_entities": bool,
        "primary_date": Optional[str],
        "primary_id": Optional[str],
        "primary_amount": Optional[float]
    }
    """
    if not text or not text.strip():
        return {
            "dates": [],
            "emails": [],
            "phone_numbers": [],
            "urls": [],
            "amounts": [],
            "ids": [],
            "aadhaar_numbers": [],
            "pan_numbers": [],
            "total_entities": 0,
            "has_entities": False,
            "primary_date": None,
            "primary_id": None,
            "primary_amount": None,
        }

    raw = text.strip()
    dates = extract_dates(raw)
    emails = extract_emails(raw)
    phones = extract_phone_numbers(raw)
    urls = extract_urls(raw)
    amounts = extract_amounts(raw)
    ids = extract_ids(raw)
    aadhaar = extract_aadhaar(raw)
    pan = extract_pan(raw)

    total_count = (
        len(dates)
        + len(emails)
        + len(phones)
        + len(urls)
        + len(amounts)
        + len(ids)
        + len(aadhaar)
        + len(pan)
    )

    primary_date = dates[0]["iso"] if dates else None
    primary_id = ids[0]["value"] if ids else (aadhaar[0] if aadhaar else (pan[0] if pan else None))
    primary_amount = amounts[0]["value"] if amounts else None

    return {
        "dates": dates,
        "emails": emails,
        "phone_numbers": phones,
        "urls": urls,
        "amounts": amounts,
        "ids": ids,
        "aadhaar_numbers": aadhaar,
        "pan_numbers": pan,
        "total_entities": total_count,
        "has_entities": total_count > 0,
        "primary_date": primary_date,
        "primary_id": primary_id,
        "primary_amount": primary_amount,
    }


def format_entities_summary(entities: Dict[str, Any]) -> str:
    """Generates a concise, human-readable summary of extracted entities."""
    parts = []
    if entities.get("dates"):
        date_strs = [d["iso"] for d in entities["dates"][:2]]
        parts.append(f"Dates: {', '.join(date_strs)}")
    if entities.get("ids"):
        id_strs = [f"{i['type']}: {i['value']}" for i in entities["ids"][:2]]
        parts.append(f"IDs: {', '.join(id_strs)}")
    if entities.get("aadhaar_numbers"):
        parts.append(f"Aadhaar: {entities['aadhaar_numbers'][0]}")
    if entities.get("pan_numbers"):
        parts.append(f"PAN: {entities['pan_numbers'][0]}")
    if entities.get("amounts"):
        amt_strs = [f"₹{int(a['value']):,}" for a in entities["amounts"][:2]]
        parts.append(f"Amounts: {', '.join(amt_strs)}")
    if entities.get("emails"):
        parts.append(f"Email: {entities['emails'][0]}")
    if entities.get("phone_numbers"):
        parts.append(f"Phone: {entities['phone_numbers'][0]}")
    if entities.get("urls"):
        parts.append(f"URL: {entities['urls'][0]}")

    return " | ".join(parts) if parts else "No entities detected"
