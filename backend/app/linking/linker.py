"""Modular cross-image relationship linking engine for document gallery (Phase 4 Step 6A).

Discovers explainable semantic relationships between distinct document images
that share reliable, high-confidence identifiers (Aadhaar, PAN, Application IDs,
Enrollment IDs, Transaction IDs, Roll Numbers, personal emails, and phone numbers).

Strict Safeguards:
- Complete isolation from duplicate detection (duplicate variants are NEVER cross-linked).
- Zero ML / classification models (purely deterministic and explainable).
- Strict rejection of weak/common words, generic dates, and public helplines.
- Non-destructive: does not delete, merge, or modify images or duplicate canonical mappings.
"""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app import database

# Blacklist of common English / OCR words that must never be treated as valid IDs
DISALLOWED_ID_VALUES: Set[str] = {
    "APEX", "ENTITY", "ENTITYCARD", "IDENTITY", "CARD", "STUDENT", "CANDIDATE",
    "FORM", "NAME", "PROCESS", "DATE", "EXAM", "CENTER", "PORTAL", "COPY",
    "APPLICANT", "VERIFICATION", "APPLICATION", "REGISTRAR", "COUNCIL",
    "DIRECTED", "ACADEMIC", "UNIVERSITY", "NOTICE", "EROF", "ROLLEROF",
    "NULL", "NONE", "UNKNOWN", "TEST", "UNDEFINED", "STUDENTIDENTITYCARD",
    "IDENTITYCARD", "SIGNATURE", "OFFICE", "COLLEGE", "INSTITUTE", "PRINCIPAL",
}

# Generic / shared email prefixes to reject
GENERIC_EMAIL_PREFIXES: Set[str] = {
    "info@", "support@", "admin@", "contact@", "help@", "noreply@", "service@",
    "mail@", "office@", "webmaster@", "sales@", "billing@",
}

# Generic helplines and invalid phone prefixes
INVALID_PHONE_PREFIXES: Tuple[str, ...] = (
    "1800", "1947", "112", "100", "101", "108",
)

# Regex to verify if an identifier contains at least one digit
CONTAINS_DIGIT = re.compile(r"\d")

# Standalone 4-digit calendar years
CALENDAR_YEARS: Set[str] = {
    "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"
}


def are_duplicates(img_a: Dict[str, Any], img_b: Dict[str, Any]) -> bool:
    """
    Determines if two image records are duplicates of each other,
    or belong to the same duplicate cluster / canonical image.

    Ensures that cross-image linking NEVER links duplicate variants together.
    """
    id_a = img_a.get("id")
    id_b = img_b.get("id")
    if id_a is None or id_b is None or id_a == id_b:
        return True

    canon_a = (
        img_a.get("canonical_image_id")
        if img_a.get("is_duplicate") and img_a.get("canonical_image_id")
        else id_a
    )
    canon_b = (
        img_b.get("canonical_image_id")
        if img_b.get("is_duplicate") and img_b.get("canonical_image_id")
        else id_b
    )

    if canon_a == canon_b:
        return True

    # Check direct canonical pointer
    if img_a.get("canonical_image_id") == id_b or img_b.get("canonical_image_id") == id_a:
        return True

    return False


def extract_strong_identifiers(entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts validated, high-confidence identifiers from an entities dictionary.
    Excludes weak tokens, common words, generic dates, and public helplines.

    Returns a list of structured identifier records:
    [
        {
            "rel_type": "shared_application_id",
            "value": "ALT-2026-SCH-9042",
            "confidence": 1.0,
            "label": "Application ID"
        },
        ...
    ]
    """
    if not isinstance(entities, dict):
        return []

    strong_ids: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str]] = set()

    # 1. Aadhaar Numbers (UIDAI 12-digit format)
    for aadhaar in entities.get("aadhaar_numbers", []):
        if not isinstance(aadhaar, str):
            continue
        cleaned = aadhaar.strip()
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) == 12 and len(set(digits)) > 1:
            norm_val = f"{digits[0:4]} {digits[4:8]} {digits[8:12]}"
            key = ("shared_aadhaar", norm_val)
            if key not in seen_keys:
                seen_keys.add(key)
                strong_ids.append({
                    "rel_type": "shared_aadhaar",
                    "value": norm_val,
                    "confidence": 1.0,
                    "label": "Aadhaar Number",
                })

    # 2. PAN Card Numbers (Indian Income Tax 10-char format)
    for pan in entities.get("pan_numbers", []):
        if not isinstance(pan, str):
            continue
        norm_val = pan.strip().upper()
        if len(norm_val) == 10:
            key = ("shared_pan", norm_val)
            if key not in seen_keys:
                seen_keys.add(key)
                strong_ids.append({
                    "rel_type": "shared_pan",
                    "value": norm_val,
                    "confidence": 1.0,
                    "label": "PAN Card",
                })

    # 3. Direct Email Addresses (Excluding generic system addresses)
    for email in entities.get("emails", []):
        if not isinstance(email, str):
            continue
        norm_val = email.strip().lower()
        if any(norm_val.startswith(p) for p in GENERIC_EMAIL_PREFIXES):
            continue
        if "@" in norm_val and len(norm_val.split("@")[0]) >= 2:
            key = ("shared_email", norm_val)
            if key not in seen_keys:
                seen_keys.add(key)
                strong_ids.append({
                    "rel_type": "shared_email",
                    "value": norm_val,
                    "confidence": 0.95,
                    "label": "Email Address",
                })

    # 4. Personal Mobile / Phone Numbers (Excluding helplines)
    for phone in entities.get("phone_numbers", []):
        if not isinstance(phone, str):
            continue
        digits = re.sub(r"\D", "", phone.strip())
        if len(digits) == 10 and len(set(digits)) > 1:
            if any(digits.startswith(p) for p in INVALID_PHONE_PREFIXES):
                continue
            if digits == "1234567890":
                continue
            key = ("shared_phone", digits)
            if key not in seen_keys:
                seen_keys.add(key)
                strong_ids.append({
                    "rel_type": "shared_phone",
                    "value": digits,
                    "confidence": 0.95,
                    "label": "Phone Number",
                })

    # 5. Structured Administrative & Academic IDs
    for id_item in entities.get("ids", []):
        if not isinstance(id_item, dict):
            continue
        raw_val = str(id_item.get("value", "")).strip(".,;:\"'#*- \t\n")
        raw_type = str(id_item.get("type", "")).strip()

        # Strict checks against weak tokens:
        # A. Length must be >= 3
        if len(raw_val) < 3:
            continue

        # B. Must contain at least one digit (prevents English words like APEX, Candidate, erof)
        if not CONTAINS_DIGIT.search(raw_val):
            continue

        # C. Must not be a standalone calendar year
        if raw_val in CALENDAR_YEARS:
            continue

        # D. Must not match disallowed blacklisted tokens
        val_upper = raw_val.upper()
        if val_upper in DISALLOWED_ID_VALUES:
            continue

        # E. Map to specific explainable relationship type
        type_lower = raw_type.lower()
        if "app" in type_lower:
            rel_type = "shared_application_id"
            label = "Application ID"
        elif "enroll" in type_lower:
            rel_type = "shared_enrollment_id"
            label = "Enrollment ID"
        elif "roll" in type_lower or "hall" in type_lower:
            rel_type = "shared_roll_number"
            label = "Roll Number"
        elif "txn" in type_lower or "transaction" in type_lower:
            rel_type = "shared_transaction_id"
            label = "Transaction ID"
        elif "student" in type_lower:
            rel_type = "shared_student_id"
            label = "Student ID"
        elif "reg" in type_lower:
            rel_type = "shared_registration_id"
            label = "Registration ID"
        else:
            rel_type = "shared_id"
            label = f"{raw_type} ID" if raw_type and raw_type != "ID" else "Document ID"

        key = (rel_type, val_upper)
        if key not in seen_keys:
            seen_keys.add(key)
            strong_ids.append({
                "rel_type": rel_type,
                "value": raw_val,
                "confidence": 1.0,
                "label": label,
            })

    return strong_ids


def find_relationships_between_images(
    img_a: Dict[str, Any], img_b: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Discovers any strong cross-image relationships between two documents.
    Enforces duplicate isolation: returns [] if images are duplicates of each other.
    """
    if are_duplicates(img_a, img_b):
        return []

    # Parse entities
    ent_a = img_a.get("entities") or {}
    if not ent_a and img_a.get("entities_json"):
        try:
            ent_a = json.loads(img_a["entities_json"])
        except Exception:
            ent_a = {}

    ent_b = img_b.get("entities") or {}
    if not ent_b and img_b.get("entities_json"):
        try:
            ent_b = json.loads(img_b["entities_json"])
        except Exception:
            ent_b = {}

    ids_a = extract_strong_identifiers(ent_a)
    ids_b = extract_strong_identifiers(ent_b)

    if not ids_a or not ids_b:
        return []

    relationships: List[Dict[str, Any]] = []
    seen_rel = set()

    for item_a in ids_a:
        for item_b in ids_b:
            # Check for value match (case-insensitive for alphanumeric strings, exact for normalized formats)
            val_a = item_a["value"].strip().upper()
            val_b = item_b["value"].strip().upper()

            if val_a == val_b:
                # Prefer the more specific relationship type
                rel_type = item_a["rel_type"]
                label = item_a["label"]
                conf = min(item_a["confidence"], item_b["confidence"])

                rel_key = (rel_type, val_a)
                if rel_key not in seen_rel:
                    seen_rel.add(rel_key)
                    relationships.append({
                        "source_image_id": img_a["id"],
                        "target_image_id": img_b["id"],
                        "relationship_type": rel_type,
                        "confidence_score": conf,
                        "evidence": item_a["value"],
                        "reason": f"Both documents share {label}: '{item_a['value']}'",
                    })

    return relationships


def link_corpus(persist: bool = True, canonical_only: bool = True) -> List[Dict[str, Any]]:
    """
    Scans the entire gallery corpus in SQLite, discovers valid cross-image relationships
    between distinct non-duplicate documents, and optionally persists them into the
    `image_relationships` table.

    When canonical_only=True (default), processes only valid canonical/non-duplicate images (is_duplicate == 0)
    for relationship discovery, ensuring zero duplicate-variant links.
    """
    all_images = database.list_images()
    if canonical_only:
        images = [img for img in all_images if not img.get("is_duplicate")]
    else:
        images = all_images

    if not images or len(images) < 2:
        return []

    discovered_relationships: List[Dict[str, Any]] = []

    # If persisting, clear existing table first for a clean state
    if persist:
        database.clear_all_relationships()

    num_images = len(images)
    for i in range(num_images):
        for j in range(i + 1, num_images):
            img_a = images[i]
            img_b = images[j]

            # Fast skip if duplicates
            if are_duplicates(img_a, img_b):
                continue

            rels = find_relationships_between_images(img_a, img_b)
            for rel in rels:
                discovered_relationships.append(rel)
                if persist:
                    database.save_relationship(
                        source_image_id=rel["source_image_id"],
                        target_image_id=rel["target_image_id"],
                        relationship_type=rel["relationship_type"],
                        confidence_score=rel["confidence_score"],
                        evidence=rel["evidence"],
                        bidirectional=True,
                    )

    return discovered_relationships


def link_image(image_id: int, persist: bool = True) -> List[Dict[str, Any]]:
    """
    Discovers relationships for a single image against all other non-duplicate
    images in the SQLite corpus.
    """
    target_image = database.get_image_by_id(image_id)
    if not target_image:
        return []

    # If target is duplicate variant, resolve to canonical
    if target_image.get("is_duplicate") and target_image.get("canonical_image_id"):
        target_image = database.get_image_by_id(target_image["canonical_image_id"])
        if not target_image:
            return []

    canonical_images = [img for img in database.list_images() if not img.get("is_duplicate")]
    discovered: List[Dict[str, Any]] = []

    for other_image in canonical_images:
        if other_image["id"] == target_image["id"]:
            continue
        if are_duplicates(target_image, other_image):
            continue

        rels = find_relationships_between_images(target_image, other_image)
        for rel in rels:
            discovered.append(rel)
            if persist:
                database.save_relationship(
                    source_image_id=rel["source_image_id"],
                    target_image_id=rel["target_image_id"],
                    relationship_type=rel["relationship_type"],
                    confidence_score=rel["confidence_score"],
                    evidence=rel["evidence"],
                    bidirectional=True,
                )

    return discovered


def get_image_relationships(image_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves all stored cross-image relationships for an image from SQLite,
    enriched with human-readable reason and target image metadata.

    If the queried image is a duplicate variant, resolves to its canonical image ID
    so that relationships discovered for the document cluster are seamlessly surfaced.
    """
    img = database.get_image_by_id(image_id)
    lookup_id = image_id
    if img and img.get("is_duplicate") and img.get("canonical_image_id"):
        lookup_id = img["canonical_image_id"]

    raw_relationships = database.get_related_images(lookup_id)
    formatted = []
    for r in raw_relationships:
        item = dict(r)
        rel_type = item.get("relationship_type", "")
        evidence = item.get("evidence", "")
        type_clean = rel_type.replace("shared_", "").replace("_", " ").title()
        item["reason"] = f"Shares {type_clean}: '{evidence}'"
        formatted.append(item)
    return formatted
