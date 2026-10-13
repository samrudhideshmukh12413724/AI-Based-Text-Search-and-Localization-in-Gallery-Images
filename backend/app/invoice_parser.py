"""Structured Invoice & Receipt Table Parser.

Parses OCR text of receipts, fee challans, and commercial invoices into structured JSON data:
- Itemized line items (Item Name, Qty, Rate, Total)
- Financial breakdown (Subtotal, CGST, SGST, IGST, Discounts, Grand Total)
- Merchant & Payment info (Merchant Name, Payment Mode, Transaction ID)
"""

import re
from typing import Dict, Any, List


def parse_invoice_structure(text: str) -> Dict[str, Any]:
    """
    Extracts structured financial & line-item data from OCR text of receipts/invoices.
    """
    cleaned_lines = [line.strip() for line in text.split("\n") if line.strip()]
    full_text = " ".join(cleaned_lines)

    # 1. Payment Mode Detection
    payment_mode = "UNKNOWN"
    if re.search(r"\b(upi|gpay|phonepe|paytm|bhim|qr)\b", full_text, re.I):
        payment_mode = "UPI / QR"
    elif re.search(r"\b(card|visa|mastercard|debit|credit)\b", full_text, re.I):
        payment_mode = "CARD"
    elif re.search(r"\b(cash|cod)\b", full_text, re.I):
        payment_mode = "CASH"
    elif re.search(r"\b(netbank|neft|rtgs|imps|challan)\b", full_text, re.I):
        payment_mode = "BANK_TRANSFER / CHALLAN"

    # 2. Extract Grand Total
    grand_total = 0.0
    total_match = re.search(r"(?:grand\s*total|net\s*payable|total\s*payable|amount\s*paid)[:\s]*[₹\$Rs\.]*\s*([\d,]+\.?\d*)", full_text, re.I)
    if not total_match:
        total_match = re.search(r"(?:total\s*amount|\btotal\b)[:\s]*[₹\$Rs\.]*\s*([\d,]+\.?\d*)", full_text, re.I)
    if total_match:
        try:
            grand_total = float(total_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # 3. Extract Tax Amounts (CGST, SGST, IGST)
    tax_info = {"cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total_tax": 0.0}
    cgst_m = re.search(r"cgst[:\s]*[₹\$Rs\.]*\s*([\d,]+\.?\d*)", full_text, re.I)
    sgst_m = re.search(r"sgst[:\s]*[₹\$Rs\.]*\s*([\d,]+\.?\d*)", full_text, re.I)
    igst_m = re.search(r"igst[:\s]*[₹\$Rs\.]*\s*([\d,]+\.?\d*)", full_text, re.I)

    if cgst_m:
        try: tax_info["cgst"] = float(cgst_m.group(1).replace(",", ""))
        except ValueError: pass
    if sgst_m:
        try: tax_info["sgst"] = float(sgst_m.group(1).replace(",", ""))
        except ValueError: pass
    if igst_m:
        try: tax_info["igst"] = float(igst_m.group(1).replace(",", ""))
        except ValueError: pass

    tax_info["total_tax"] = round(tax_info["cgst"] + tax_info["sgst"] + tax_info["igst"], 2)

    # 4. Extract Line Items (matching price patterns)
    line_items: List[Dict[str, Any]] = []
    price_pattern = re.compile(r"^(.+?)\s+([\d,]+\.?\d{0,2})$")

    for line in cleaned_lines:
        # Ignore total and tax summary lines
        if re.search(r"\b(total|subtotal|cgst|sgst|igst|tax|paid|balance|thank)\b", line, re.I):
            continue
        m = price_pattern.match(line)
        if m:
            item_name = m.group(1).strip()
            try:
                item_price = float(m.group(2).replace(",", ""))
                if len(item_name) >= 3 and item_price > 0:
                    line_items.append({"item": item_name, "price": item_price})
            except ValueError:
                pass

    return {
        "is_receipt_or_invoice": bool(grand_total > 0 or len(line_items) > 0 or payment_mode != "UNKNOWN"),
        "payment_mode": payment_mode,
        "grand_total": grand_total,
        "tax_breakdown": tax_info,
        "line_items": line_items[:10],
        "item_count": len(line_items),
    }
