"""Multi-Lingual Indic Language Auto-Translation & Query Expansion Module.

Detects Devanagari script (Hindi / Marathi) and regional vocabulary in OCR text
and provides automated English translation and cross-lingual query expansion.
"""

import re
from typing import Dict, Any, List

# Key vocabulary translation mapping for common document terms (Hindi/Marathi to English)
INDIC_TRANSLATION_MAP = {
    # Educational & Academic
    "छात्रवृत्ति": "scholarship",
    "शिष्यवृत्ती": "scholarship",
    "प्रवेश": "admission",
    "परीक्षा": "examination",
    "हॉल टिकट": "hall ticket / admit card",
    "प्रवेश पत्र": "admit card",
    "अंकपत्र": "marksheet / grade card",
    "गुणपत्रक": "marksheet",
    "प्रमाणपत्र": "certificate",
    "शुल्क": "fees",
    "पावती": "receipt",
    "रसीद": "receipt",
    "चालान": "challan",
    "विद्यार्थी": "student",
    "महाविद्यालय": "college / university",
    "सूचना": "notice / announcement",
    "वेळापत्रक": "timetable / schedule",
    "समय सारणी": "timetable",
    # Personal & Identifiers
    "आधार": "aadhaar",
    "ओळखपत्र": "identity card",
    "पैन": "pan card",
    "जन्म तारीख": "date of birth",
    "पत्ता": "address",
    "रक्कम": "amount",
    "एकूण": "total",
}

# Reverse mapping from English terms to Indic vocabulary
ENGLISH_TO_INDIC_MAP: Dict[str, List[str]] = {}
for indic_k, eng_v in INDIC_TRANSLATION_MAP.items():
    for term in re.split(r"[\s/]+", eng_v.lower()):
        term = term.strip()
        if len(term) >= 3:
            ENGLISH_TO_INDIC_MAP.setdefault(term, []).append(indic_k)


def is_devanagari(text: str) -> bool:
    """Checks if text contains Devanagari (Hindi/Marathi) Unicode characters."""
    return bool(re.search(r"[\u0900-\u097F]", text))


def get_query_expansions(query: str) -> List[str]:
    """Expands query across Marathi and English so searching either language matches the other."""
    expansions = [query]
    q_clean = query.strip()
    q_lower = q_clean.lower()

    # 1. Indic -> English
    for k, v in INDIC_TRANSLATION_MAP.items():
        if k in q_clean:
            for eng_part in re.split(r"[\s/]+", v):
                eng_part = eng_part.strip()
                if len(eng_part) >= 3 and eng_part not in expansions:
                    expansions.append(eng_part)

    # 2. English -> Indic
    for eng_word in re.findall(r"[a-zA-Z]+", q_lower):
        if eng_word in ENGLISH_TO_INDIC_MAP:
            for ind in ENGLISH_TO_INDIC_MAP[eng_word]:
                if ind not in expansions:
                    expansions.append(ind)

    return expansions


def translate_indic_text(text: str) -> Dict[str, Any]:
    """
    Translates Indic (Hindi/Marathi) document terms to English and builds translated searchable text.
    """
    has_indic = is_devanagari(text)
    translations_found: List[str] = []

    for key, val in INDIC_TRANSLATION_MAP.items():
        if key in text:
            translations_found.append(f"{key} -> {val}")

    translated_terms = " ".join([val for key, val in INDIC_TRANSLATION_MAP.items() if key in text])

    return {
        "has_indic_script": has_indic,
        "translated_terms": translated_terms,
        "translations_found": translations_found,
        "searchable_translated_text": f"{text} {translated_terms}".strip(),
    }
