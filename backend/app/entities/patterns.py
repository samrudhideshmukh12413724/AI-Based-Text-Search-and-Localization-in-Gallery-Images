"""High-precision regex patterns and normalization utilities for document entity extraction.

Extracts:
- Dates (numerical DD/MM/YYYY, YYYY-MM-DD, and textual e.g. '15th Sept 2026')
- Email addresses
- Indian and international Phone numbers
- URLs and web endpoints
- Monetary Amounts (₹, Rs., INR, with fee/stipend context)
- Academic and administrative IDs (Roll Numbers, Hall Tickets, Application Numbers, TXN)
- Aadhaar Numbers (12-digit UIDAI compliant)
- PAN Cards (10-char Indian Income Tax format with 4th-char status validation)
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

# Month mapping for textual dates
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# ---------------------------------------------------------------------------
# 1. DATE EXTRACTION & NORMALIZATION
# ---------------------------------------------------------------------------

# Numerical: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
DATE_NUM_DMY = re.compile(
    r"\b(0?[1-9]|[12][0-9]|3[01])[-/.](0?[1-9]|1[012])[-/.]((?:19|20)\d\d)\b"
)

# Numerical: YYYY-MM-DD, YYYY/MM/DD
DATE_NUM_YMD = re.compile(
    r"\b((?:19|20)\d\d)[-/.](0?[1-9]|1[012])[-/.](0?[1-9]|[12][0-9]|3[01])\b"
)

# Textual: 15th September 2026, 12-Feb-2026, 2Oth February 2026 (handles OCR 'O' for '0')
DATE_TEXTUAL = re.compile(
    r"\b([0-3]?[0-9Oo])(?:st|nd|rd|th)?[\s.-]+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s,.-]+((?:19|20)\d\d)\b",
    re.IGNORECASE,
)

# Month Year only: March 2026, September 2025
DATE_MONTH_YEAR = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s,]+((?:19|20)\d\d)\b",
    re.IGNORECASE,
)


def normalize_date(year: int, month: int, day: Optional[int] = None) -> Optional[str]:
    """Validates and formats a date into ISO 8601 (YYYY-MM-DD or YYYY-MM)."""
    try:
        if day is not None:
            dt = datetime(year, month, day)
            return dt.strftime("%Y-%m-%d")
        else:
            return f"{year:04d}-{month:02d}"
    except ValueError:
        return None


def extract_dates(text: str) -> List[Dict[str, Any]]:
    """Extracts all recognized dates with raw text and normalized ISO format."""
    results = []
    seen_iso = set()

    # 1. Textual dates (e.g. 15th September 2026, 2Oth Feb 2026)
    for m in DATE_TEXTUAL.finditer(text):
        raw_day = m.group(1).upper().replace("O", "0")
        raw_month = m.group(2).lower()
        raw_year = int(m.group(3))
        try:
            day = int(raw_day)
            month = MONTH_MAP.get(raw_month[:3])
            if month and 1 <= day <= 31:
                iso = normalize_date(raw_year, month, day)
                if iso and iso not in seen_iso:
                    seen_iso.add(iso)
                    results.append({"raw": m.group(0).strip(), "iso": iso, "precision": "day"})
        except ValueError:
            continue

    # 2. Numerical DD/MM/YYYY
    for m in DATE_NUM_DMY.finditer(text):
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        iso = normalize_date(year, month, day)
        if iso and iso not in seen_iso:
            seen_iso.add(iso)
            results.append({"raw": m.group(0).strip(), "iso": iso, "precision": "day"})

    # 3. Numerical YYYY-MM-DD
    for m in DATE_NUM_YMD.finditer(text):
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        iso = normalize_date(year, month, day)
        if iso and iso not in seen_iso:
            seen_iso.add(iso)
            results.append({"raw": m.group(0).strip(), "iso": iso, "precision": "day"})

    # 4. Month + Year only (e.g. March 2026)
    for m in DATE_MONTH_YEAR.finditer(text):
        raw_month = m.group(1).lower()
        raw_year = int(m.group(2))
        month = MONTH_MAP.get(raw_month[:3])
        if month:
            iso = normalize_date(raw_year, month, None)
            if iso and not any(s.startswith(iso) for s in seen_iso):
                seen_iso.add(iso)
                results.append({"raw": m.group(0).strip(), "iso": iso, "precision": "month"})

    return results


# ---------------------------------------------------------------------------
# 2. EMAIL ADDRESS EXTRACTION
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def extract_emails(text: str) -> List[str]:
    """Extracts valid, unique lowercase email addresses."""
    matches = EMAIL_PATTERN.findall(text)
    cleaned = []
    seen = set()
    for e in matches:
        e_clean = e.strip(".,;:").lower()
        if e_clean not in seen and len(e_clean.split("@")[-1]) >= 3:
            seen.add(e_clean)
            cleaned.append(e_clean)
    return cleaned


# ---------------------------------------------------------------------------
# 3. PHONE NUMBER EXTRACTION (Indian + International)
# ---------------------------------------------------------------------------

PHONE_INDIAN_MOBILE = re.compile(
    r"(?:\+91[\s.-]?)?([6-9]\d{4}[\s.-]?\d{5})\b"
)

PHONE_CONTEXT = re.compile(
    r"(?:Phone|Contact|Mobile|Tel|Cell|Call)\s*[:#-]?\s*(\+?[0-9\s.-]{8,16})",
    re.IGNORECASE,
)


def extract_phone_numbers(text: str) -> List[str]:
    """Extracts standardized phone numbers, prioritizing Indian mobile formats."""
    results = []
    seen = set()

    for m in PHONE_CONTEXT.finditer(text):
        raw = m.group(1).strip()
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 12:
            if len(set(digits)) > 1:
                norm = digits[-10:] if len(digits) == 10 or (len(digits) == 12 and digits.startswith("91")) else digits
                if norm not in seen:
                    seen.add(norm)
                    results.append(norm)

    for m in PHONE_INDIAN_MOBILE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) == 10 and digits[0] in "6789" and len(set(digits)) > 1:
            if digits not in seen:
                seen.add(digits)
                results.append(digits)

    return results


# ---------------------------------------------------------------------------
# 4. URL EXTRACTION
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s,;<>]*)?\b",
    re.IGNORECASE,
)


def extract_urls(text: str) -> List[str]:
    """Extracts valid web URLs, ensuring standard scheme."""
    matches = URL_PATTERN.findall(text)
    cleaned = []
    seen = set()
    for u in matches:
        u_clean = u.strip(".,;:\"')")
        if u_clean.startswith("www."):
            u_clean = "https://" + u_clean
        if u_clean.lower() not in seen:
            seen.add(u_clean.lower())
            cleaned.append(u_clean)
    return cleaned


# ---------------------------------------------------------------------------
# 5. MONETARY AMOUNTS / CURRENCY EXTRACTION
# ---------------------------------------------------------------------------

AMOUNT_EXPLICIT = re.compile(
    r"(?:\u20b9|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/-)?",
    re.IGNORECASE,
)

AMOUNT_CONTEXT = re.compile(
    r"(?:Fee|Amount|Paid|Total|Scholarship|Grant|Stipend|Penalty|Price)\s*[:#-]?\s*(?:\u20b9|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:/-)?",
    re.IGNORECASE,
)


def extract_amounts(text: str) -> List[Dict[str, Any]]:
    """Extracts monetary values, parsed into numerical floats and normalized currency."""
    results = []
    seen_values = set()

    for m in AMOUNT_EXPLICIT.finditer(text):
        raw_val = m.group(1).replace(",", "")
        try:
            val = float(raw_val)
            if val >= 1.0 and val not in seen_values:
                seen_values.add(val)
                results.append({
                    "raw": m.group(0).strip(),
                    "value": val,
                    "currency": "INR",
                })
        except ValueError:
            continue

    for m in AMOUNT_CONTEXT.finditer(text):
        raw_val = m.group(1).replace(",", "")
        try:
            val = float(raw_val)
            if val >= 10.0 and val not in seen_values and val not in {2024, 2025, 2026, 2027}:
                seen_values.add(val)
                results.append({
                    "raw": m.group(0).strip(),
                    "value": val,
                    "currency": "INR",
                })
        except ValueError:
            continue

    return results


# ---------------------------------------------------------------------------
# 6. IDENTIFIERS & ROLL NUMBERS EXTRACTION
# ---------------------------------------------------------------------------

ID_DISALLOWED = {
    "FORM", "NAME", "STUDENT", "PROCESS", "CARD", "DATE", "EXAM",
    "CENTER", "PORTAL", "COPY", "APPLICANT", "VERIFICATION", "APPLICATION",
    "REGISTRAR", "COUNCIL", "DIRECTED", "ACADEMIC", "UNIVERSITY", "NOTICE"
}

ID_CONTEXT = re.compile(
    r"(?:Roll\s*(?:No\.?|Number|ID|#)?|Hall\s*Ticket(?:\s*ID|\s*No\.?)?|App(?:lication)?\s*(?:No\.?|Number|ID|#)|Enrollment(?:\s*No\.?|\s*ID)?|Reg(?:istration)?\s*(?:No\.?|Number|ID|#)|Transaction\s*(?:Ref|ID|No\.?)|TXN(?:\s*Ref|\s*ID|\s*No\.?)?|Student\s*ID|\bID\s*[:#-])\s*[:#-]?\s*([A-Za-z0-9/-]{2,25})",
    re.IGNORECASE,
)

ROLL_NUMBER_PATTERN = re.compile(
    r"\b(\d{2}[A-Za-z]{2,5}\d{2,4})\b"
)


def extract_ids(text: str) -> List[Dict[str, str]]:
    """Extracts structured academic, candidate, and transactional identifiers."""
    results = []
    seen = set()

    for m in ID_CONTEXT.finditer(text):
        label = m.group(0).split(":")[0].split("-")[0].strip()
        val = m.group(1).strip(".,;:- ")
        if val.upper() in ID_DISALLOWED or (val.isalpha() and len(val) < 4):
            continue
        if len(val) >= 2 and val.upper() not in seen:
            seen.add(val.upper())
            results.append({"type": label, "value": val})

    for m in ROLL_NUMBER_PATTERN.finditer(text):
        val = m.group(1).strip()
        if val.upper() not in seen:
            seen.add(val.upper())
            results.append({"type": "Roll Number", "value": val.upper()})

    return results


# ---------------------------------------------------------------------------
# 7. AADHAAR NUMBER EXTRACTION
# ---------------------------------------------------------------------------

AADHAAR_PATTERN = re.compile(
    r"\b([2-9]\d{3}\s\d{4}\s\d{4})\b"
)

AADHAAR_CONTEXT = re.compile(
    r"(?:Aadhaar|UIDAI|UID)\s*(?:No\.?|Number)?\s*[:#-]?\s*([2-9]\d{3}\s?\d{4}\s?\d{4})",
    re.IGNORECASE,
)


def extract_aadhaar(text: str) -> List[str]:
    """Extracts 12-digit Aadhaar numbers normalized to 'XXXX XXXX XXXX'."""
    results = []
    seen = set()

    for pattern in (AADHAAR_PATTERN, AADHAAR_CONTEXT):
        for m in pattern.finditer(text):
            digits = re.sub(r"\D", "", m.group(1))
            if len(digits) == 12 and digits[0] not in "01":
                formatted = f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
                if formatted not in seen:
                    seen.add(formatted)
                    results.append(formatted)

    return results


# ---------------------------------------------------------------------------
# 8. PAN (PERMANENT ACCOUNT NUMBER) EXTRACTION
# ---------------------------------------------------------------------------

PAN_PATTERN = re.compile(
    r"\b([A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z])\b"
)


def extract_pan(text: str) -> List[str]:
    """Extracts valid Indian PAN card identifiers."""
    matches = PAN_PATTERN.findall(text)
    cleaned = []
    seen = set()
    for p in matches:
        if p not in seen:
            seen.add(p)
            cleaned.append(p)
    return cleaned
