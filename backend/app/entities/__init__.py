"""Document Entities Extraction Package.

Extracts structured information from OCR text:
- Dates (numerical & textual normalized to ISO 8601)
- Email addresses
- Phone numbers (Indian mobile & landline)
- URLs
- Monetary amounts & currency
- IDs & Roll numbers
- Aadhaar & PAN card numbers
"""

from app.entities.extractor import extract_entities, format_entities_summary
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

__all__ = [
    "extract_entities",
    "format_entities_summary",
    "extract_dates",
    "extract_emails",
    "extract_phone_numbers",
    "extract_urls",
    "extract_amounts",
    "extract_ids",
    "extract_aadhaar",
    "extract_pan",
]
