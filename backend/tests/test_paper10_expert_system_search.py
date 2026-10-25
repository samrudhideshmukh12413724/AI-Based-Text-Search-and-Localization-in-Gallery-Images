"""Unit Tests for Paper 10: Expert System & Full-Text Search Integration.

Reference:
  Abdelrahman Elsayed, Maryam Hazman, Susan F. Ellakwa
  "Integrating expert system with a full-text search to solve growers' problems"
  2019 15th International Computer Engineering Conference (ICENCO), IEEE.

Covers:
1. Forward-Chaining Inference & Certainty Factor (CF) Propagation.
2. Utility Overdue Detection & 1-Tap UPI Settlement Action.
3. Official Helpline Customer Care Dialing Action.
4. Merchant Invoice GSTIN & Instant UPI Payment URI.
5. Government ID Masking (PAN & Aadhaar UIDAI Compliance).
6. Medical Prescription Recognition & Digital Pharmacy Action.
7. Academic Credential Verification (CGPA & Roll Number).
8. Zero-Hallucination Visual Attribution (Bounding Box Polygon Linking).
9. Transparent Explanation Facility (Inference Trail & Rule Audit).
"""

import pytest
from app.expert_system import (
    DocumentExpertSystem,
    solve_document_problem,
)


@pytest.fixture
def expert_system():
    return DocumentExpertSystem()


@pytest.fixture
def sample_ocr_boxes():
    return [
        {"text": "MSEDCL", "ymin": 30, "xmin": 50, "ymax": 55, "xmax": 150},
        {"text": "Electricity", "ymin": 30, "xmin": 160, "ymax": 55, "xmax": 260},
        {"text": "Bill", "ymin": 30, "xmin": 270, "ymax": 55, "xmax": 320},
        {"text": "Consumer", "ymin": 80, "xmin": 50, "ymax": 105, "xmax": 140},
        {"text": "No:", "ymin": 80, "xmin": 145, "ymax": 105, "xmax": 175},
        {"text": "028510001234", "ymin": 80, "xmin": 185, "ymax": 105, "xmax": 310},
        {"text": "Grand", "ymin": 130, "xmin": 50, "ymax": 155, "xmax": 110},
        {"text": "Total:", "ymin": 130, "xmin": 115, "ymax": 155, "xmax": 170},
        {"text": "Rs", "ymin": 130, "xmin": 180, "ymax": 155, "xmax": 205},
        {"text": "2450.00", "ymin": 130, "xmin": 210, "ymax": 155, "xmax": 290},
        {"text": "Due", "ymin": 170, "xmin": 50, "ymax": 195, "xmax": 90},
        {"text": "Date:", "ymin": 170, "xmin": 95, "ymax": 195, "xmax": 145},
        {"text": "12-10-2026", "ymin": 170, "xmin": 155, "ymax": 195, "xmax": 255},
        {"text": "Helpline:", "ymin": 210, "xmin": 50, "ymax": 235, "xmax": 140},
        {"text": "1800-233-3435", "ymin": 210, "xmin": 150, "ymax": 235, "xmax": 295},
    ]


def test_forward_chaining_utility_bill_overdue_action(expert_system, sample_ocr_boxes):
    """
    Paper 10 Core Rule: Evaluates overdue utility bill condition and synthesizes
    1-tap UPI payment deep link with high certainty factor.
    """
    doc_text = (
        "MSEDCL Electricity Bill. Consumer No: 028510001234. "
        "Grand Total: Rs 2,450.00. Due Date: 12-10-2026. "
        "Helpline: 1800-233-3435."
    )

    result = expert_system.diagnose_and_solve(
        document_text=doc_text,
        ocr_boxes=sample_ocr_boxes,
        problem_query="electricity bill overdue fine",
    )

    assert result["status"] == "success"
    assert result["primary_domain"] == "Utility & Electricity Bills"
    assert result["overall_confidence"] >= 0.85

    # Check triggered rules
    rule_ids = [r["rule_id"] for r in result["triggered_rules"]]
    assert "UB01" in rule_ids
    assert "UB02" in rule_ids

    # Check action chips
    action_types = [a["type"] for a in result["action_chips"]]
    assert "PAY_UPI" in action_types
    assert "CALL_PHONE" in action_types

    upi_action = next(a for a in result["action_chips"] if a["type"] == "PAY_UPI")
    assert "2450.00" in upi_action["uri"]
    assert "upi://pay" in upi_action["uri"]


def test_helpline_direct_dial_action(expert_system):
    """Validates Rule UB02: Direct telephone URI creation for 1-tap dialer."""
    doc_text = "Adani Electricity Bill. Consumer Number: CA-992100. Helpline: 19122. Pay before disconnection."
    result = expert_system.diagnose_and_solve(doc_text, problem_query="customer care complaint")

    phone_action = next((a for a in result["action_chips"] if a["type"] == "CALL_PHONE"), None)
    assert phone_action is not None
    assert "19122" in phone_action["uri"]
    assert phone_action["uri"].startswith("tel:")


def test_merchant_invoice_upi_and_gst_compliance(expert_system):
    """
    Validates Rules INV01 & INV02:
    - Extracts verified GSTIN for Input Tax Credit.
    - Generates 1-tap merchant payment link.
    """
    invoice_text = (
        "Tax Invoice No: INV-2026-8819\n"
        "Shree Ganesh Hardware & Electricals\n"
        "GSTIN: 27ABCDE1234F1Z5\n"
        "UPI ID: shreeganesh@icici\n"
        "Total Amount: ₹12,490.00\n"
        "Due Date: 30-11-2026"
    )

    result = expert_system.diagnose_and_solve(invoice_text, problem_query="tax invoice itc")

    rule_ids = [r["rule_id"] for r in result["triggered_rules"]]
    assert "INV01" in rule_ids
    assert "INV02" in rule_ids

    gst_action = next(a for a in result["action_chips"] if a["type"] == "COPY_TEXT")
    assert gst_action["payload"] == "27ABCDE1234F1Z5"

    upi_action = next(a for a in result["action_chips"] if a["type"] == "PAY_UPI")
    assert "shreeganesh@icici" in upi_action["uri"]
    assert "12490.00" in upi_action["uri"]


def test_privacy_masked_pan_and_aadhaar(expert_system):
    """
    Validates Rules ID01 & ID02:
    - Strict masking for Indian PAN Card (ABXXXXX12C).
    - Strict masking for Aadhaar Number (XXXX-XXXX-9901).
    """
    gov_id_text = "Income Tax Department Govt of India. PAN: ABCDE1234F. Name: Rahul Sharma."
    res_pan = expert_system.diagnose_and_solve(gov_id_text)

    pan_action = next(a for a in res_pan["action_chips"] if a["type"] == "COPY_MASKED")
    assert pan_action["masked_display"] == "ABXXXXX34F"
    assert pan_action["payload"] == "ABCDE1234F"

    aadhaar_text = "Government of India. Unique Identification Authority of India. Aadhaar: 9812 3456 9901."
    res_aadhaar = expert_system.diagnose_and_solve(aadhaar_text)

    aadhaar_action = next(a for a in res_aadhaar["action_chips"] if a["type"] == "COPY_MASKED")
    assert aadhaar_action["masked_display"] == "XXXX-XXXX-9901"


def test_medical_prescription_and_healthcare_action(expert_system):
    """
    Validates Rule MED01:
    - Identifies medical prescriptions and consult notes.
    - Generates 1-tap digital pharmacy action.
    """
    med_text = (
        "Max Healthcare Super Specialty Hospital\n"
        "Doctor: Dr. Sunita Kulkarni MD (Medicine)\n"
        "Rx: Azithromycin 500mg once daily for 5 days\n"
        "Tab Paracetamol 650mg as needed for fever\n"
        "Helpline: +91-20-66001234"
    )

    result = expert_system.diagnose_and_solve(med_text, problem_query="fever prescription tablets")

    assert result["primary_domain"] == "Medical & Healthcare"
    med_action = next((a for a in result["action_chips"] if a["type"] == "HEALTH_ACTION"), None)
    assert med_action is not None
    assert "Sunita Kulkarni" in med_action["label"]


def test_academic_marksheet_credential_verification(expert_system):
    """
    Validates Rule ACD01:
    - Extracts academic transcripts, roll numbers, and CGPA.
    - Synthesizes student credential verification payload.
    """
    transcript_text = (
        "Vishwakarma Institute of Technology, Pune\n"
        "Autonomous Institute Affiliated to Savitribai Phule Pune University\n"
        "Semester VIII Grade Sheet\n"
        "Student Name: Samrudhi Deshmukh\n"
        "Roll No: 08\n"
        "Final Cumulative Grade Point Average (CGPA): 9.85\n"
        "Result: PASS WITH DISTINCTION"
    )

    result = expert_system.diagnose_and_solve(transcript_text, problem_query="engineering marksheet grade")

    assert result["primary_domain"] == "Academic & Educational"
    acad_action = next((a for a in result["action_chips"] if a["type"] == "ACADEMIC_VERIFY"), None)
    assert acad_action is not None
    assert "Roll: 08" in acad_action["payload"]
    assert "9.85" in acad_action["payload"]


def test_zero_hallucination_visual_attribution(expert_system, sample_ocr_boxes):
    """
    Overcomes Paper 10 Clean-Text limitation:
    Verifies that every extracted fact is visually verified with an exact bounding box.
    """
    doc_text = "MSEDCL Electricity Bill. Consumer No: 028510001234. Grand Total: Rs 2450.00. Due Date: 12-10-2026."
    result = expert_system.diagnose_and_solve(doc_text, ocr_boxes=sample_ocr_boxes)

    proofs = result["visual_proofs"]
    assert "amount" in proofs
    assert proofs["amount"]["grounding_status"] == "VERIFIED_ON_IMAGE"
    assert "ymin" in proofs["amount"]["bounding_box"]

    assert "due_date" in proofs
    assert proofs["due_date"]["grounding_status"] == "VERIFIED_ON_IMAGE"


def test_explanation_facility_audit_trail(expert_system):
    """
    Paper 10 Explanation Facility Requirement:
    System must produce a human-verifiable reasoning trail explaining which rules fired
    and how the certainty factors were combined.
    """
    doc_text = "Tax Invoice No: 9941. Amount: ₹5,000.00. UPI: store@paytm. Due Date: 20-11-2026."
    result = expert_system.diagnose_and_solve(doc_text, problem_query="invoice payment store")

    explanation = result["explanation_facility"]
    assert explanation["rules_evaluated"] > 0
    assert explanation["rules_fired_count"] >= 2
    assert len(explanation["inference_chain"]) >= 2
    assert explanation["fts_relevance_score"] > 0

    # Verify each chain item documents rule ID and certainty factor
    for chain_entry in explanation["inference_chain"]:
        assert "CF=" in chain_entry


def test_public_solve_document_problem_functional_wrapper():
    """Validates top-level solve_document_problem wrapper."""
    doc_text = "Aadhaar Card. Government of India. Unique ID: 1234 5678 9012."
    res = solve_document_problem(doc_text)
    assert res["status"] == "success"
    assert "Government Identity" in [r["domain"] for r in res["triggered_rules"]]
