"""Multi-Lingual Indic Language Auto-Translation & Query Expansion Module.

Detects Devanagari script (Hindi / Marathi) and regional vocabulary in OCR text
and provides automated English translation and cross-lingual query expansion.
Supports code-mixed English + Marathi (Bilingual) documents and search queries.
"""

import re
from typing import Dict, Any, List

# Comprehensive vocabulary translation mapping for common document terms (Hindi/Marathi to English)
INDIC_TRANSLATION_MAP = {
    # Geographic & Regional
    "पुणे": "pune",
    "मुंबई": "mumbai",
    "महाराष्ट्र": "maharashtra",
    "उस्मानाबाद": "osmanabad",
    "धाराशिव": "dharashiv",
    "सोलापूर": "solapur",
    "नागपूर": "nagpur",
    "नाशिक": "nashik",
    "औरंगाबाद": "aurangabad",
    "संभाजीनगर": "sambhajinagar",
    "भारत": "india",

    # Travel, Transport & Tickets
    "बस": "bus",
    "तिकीट": "ticket",
    "प्रवासी": "passenger",
    "चालक": "driver",
    "ड्रायव्हर": "driver",
    "मार्ग": "route",
    "पिकअप": "pickup",
    "स्थानक": "station",
    "ठिकाण": "location",
    "गाडी": "vehicle / bus",

    # Educational & Academic
    "छात्रवृत्ति": "scholarship",
    "शिष्यवृत्ती": "scholarship",
    "प्रवेश": "admission",
    "परीक्षा": "examination / exam",
    "हॉल टिकट": "hall ticket / admit card",
    "प्रवेश पत्र": "admit card",
    "अंकपत्र": "marksheet / grade card",
    "गुणपत्रक": "marksheet",
    "प्रमाणपत्र": "certificate",
    "शुल्क": "fees / fee",
    "पावती": "receipt",
    "रसीद": "receipt",
    "चालान": "challan",
    "विद्यार्थी": "student",
    "महाविद्यालय": "college",
    "विद्यापीठ": "university",
    "सूचना": "notice / announcement",
    "वेळापत्रक": "timetable / schedule",
    "समय सारणी": "timetable",
    "विभाग": "department",
    "अभियांत्रिकी": "engineering",
    "तंत्रज्ञान": "technology",
    "पदवी": "degree",
    "नियमित": "regular",
    "निकाल": "result",
    "हजेरी": "attendance",
    "वसतिगृह": "hostel",
    "ग्रंथालय": "library",

    # Personal & Identifiers
    "आधार": "aadhaar",
    "ओळखपत्र": "identity card / id",
    "पैन": "pan card",
    "जन्म तारीख": "date of birth",
    "पत्ता": "address",
    "नाव": "name",
    "रक्कम": "amount",
    "एकूण": "total",
    "दिनांक": "date",
    "तारीख": "date",
    "वेळ": "time",
    "वर्ष": "year",
    "महिना": "month",
    "क्रमांक": "number / no",
    "नंबर": "number",
    "भ्रमणध्वनी": "mobile / phone",
    "दूरध्वनी": "telephone / phone",
    "मोबाईल": "mobile",
    "स्वाक्षरी": "signature / sign",
    "सही": "signature / sign",
    "शिक्का": "stamp / seal",
    "मुद्रा": "seal",
    "वय": "age",
    "लिंग": "gender",

    # Banking & Official
    "बँक": "bank",
    "खाते": "account",
    "शाखा": "branch",
    "देयक": "bill / invoice",
    "अर्ज": "application",
    "शासन": "government",
    "शासकीय": "government",
    "रद्द": "cancelled",
    "यशस्वी": "successful",
}

# Reverse mapping from English terms to Indic vocabulary
ENGLISH_TO_INDIC_MAP: Dict[str, List[str]] = {}
for indic_k, eng_v in INDIC_TRANSLATION_MAP.items():
    for term in re.split(r"[\s/]+", eng_v.lower()):
        term = term.strip()
        if len(term) >= 2:
            ENGLISH_TO_INDIC_MAP.setdefault(term, []).append(indic_k)


def is_devanagari(text: str) -> bool:
    """Checks if text contains Devanagari (Hindi/Marathi) Unicode characters."""
    return bool(re.search(r"[\u0900-\u097F]", text))


def get_query_expansions(query: str) -> List[str]:
    """
    Expands query across Marathi and English so searching either language matches the other.
    Handles code-mixed queries (e.g. 'bus तिकीट', 'exam शुल्क', 'Pune पावती').
    """
    expansions: List[str] = [query.strip()]
    q_clean = query.strip()
    q_lower = q_clean.lower()

    # 1. Exact phrase mapping
    for k, v in INDIC_TRANSLATION_MAP.items():
        if k in q_clean:
            for eng_part in re.split(r"[\s/]+", v):
                eng_part = eng_part.strip()
                if len(eng_part) >= 2 and eng_part not in expansions:
                    expansions.append(eng_part)

    # 2. Token-level bidirectional translation for code-mixed queries
    # Find all Devanagari words in query
    devanagari_tokens = re.findall(r"[\u0900-\u097F]+", q_clean)
    for dev_tok in devanagari_tokens:
        if dev_tok in INDIC_TRANSLATION_MAP:
            eng_equiv = INDIC_TRANSLATION_MAP[dev_tok]
            for ep in re.split(r"[\s/]+", eng_equiv):
                ep = ep.strip()
                if len(ep) >= 2 and ep not in expansions:
                    expansions.append(ep)

    # Find all English words in query
    english_tokens = re.findall(r"[a-zA-Z]+", q_lower)
    for eng_tok in english_tokens:
        if eng_tok in ENGLISH_TO_INDIC_MAP:
            for ind_equiv in ENGLISH_TO_INDIC_MAP[eng_tok]:
                if ind_equiv not in expansions:
                    expansions.append(ind_equiv)

    # 3. Construct cross-lingual synthetic query combinations for multi-word queries
    if len(devanagari_tokens) > 0 and len(english_tokens) > 0:
        # Code-mixed query like "bus तिकीट" -> generate full English "bus ticket"
        mixed_to_eng = q_clean
        for dev_tok in devanagari_tokens:
            if dev_tok in INDIC_TRANSLATION_MAP:
                first_eng = re.split(r"[\s/]+", INDIC_TRANSLATION_MAP[dev_tok])[0]
                mixed_to_eng = mixed_to_eng.replace(dev_tok, first_eng)
        if mixed_to_eng != q_clean and mixed_to_eng not in expansions:
            expansions.append(mixed_to_eng)

        # Code-mixed query like "bus तिकीट" -> generate full Indic "बस तिकीट"
        mixed_to_ind = q_clean
        for eng_tok in english_tokens:
            if eng_tok in ENGLISH_TO_INDIC_MAP:
                first_ind = ENGLISH_TO_INDIC_MAP[eng_tok][0]
                mixed_to_ind = re.sub(rf"\b{re.escape(eng_tok)}\b", first_ind, mixed_to_ind, flags=re.IGNORECASE)
        if mixed_to_ind != q_clean and mixed_to_ind not in expansions:
            expansions.append(mixed_to_ind)

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
