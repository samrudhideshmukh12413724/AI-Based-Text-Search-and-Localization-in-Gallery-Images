"""Financial Amount Range Filter Engine.

Filters document candidates based on monetary amounts extracted from receipt/invoice text
or structured entities (e.g. min_amount <= amount <= max_amount).
"""

import re
from typing import List, Dict, Any, Optional


def extract_amounts_from_text(text: str) -> List[float]:
    """Extracts numerical currency amounts from document text."""
    matches = re.findall(r"(?:₹|\$|Rs\.?|INR)?\s*([\d,]+\.?\d{0,2})", text, re.IGNORECASE)
    amounts: List[float] = []
    for m in matches:
        clean = m.replace(",", "").strip()
        if clean:
            try:
                val = float(clean)
                if 1.0 <= val <= 1000000.0:  # Valid financial range
                    amounts.append(val)
            except ValueError:
                pass
    return amounts


def filter_by_amount_range(
    candidates: List[Dict[str, Any]],
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filters document candidates to those containing financial amounts within [min_amount, max_amount].
    """
    if min_amount is None and max_amount is None:
        return candidates

    filtered = []
    for doc in candidates:
        text = f"{doc.get('extracted_text', '')} {doc.get('matched_text', '')}"
        doc_amounts = extract_amounts_from_text(text)

        # Include structured invoice grand total if available
        inv_data = doc.get("invoice_data", {})
        if isinstance(inv_data, dict) and inv_data.get("grand_total", 0) > 0:
            doc_amounts.append(float(inv_data["grand_total"]))

        if not doc_amounts:
            continue

        match = False
        for amt in doc_amounts:
            valid_min = (min_amount is None) or (amt >= min_amount)
            valid_max = (max_amount is None) or (amt <= max_amount)
            if valid_min and valid_max:
                match = True
                break

        if match:
            filtered.append(doc)

    return filtered
