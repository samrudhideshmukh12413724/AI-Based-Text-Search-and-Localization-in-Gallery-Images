"""Unit tests for Paper 7: Search Desk Architecture & Enhancements.

Directly tests the research implementation resolving:
Paper 7: Efficient Data Searching and Management with Search Desk: A Customizable Search Engine for Accurate and Timely Results
(Kumar et al., IEEE ICCCNT 2023, IIT Delhi)

Covers:
1. Keyword-based Naive Bayes Classification with Laplace Smoothing (+1/+2).
2. Multi-Format Deep Magic-Byte Identification (11 file formats).
3. Zero-Duplication In-Memory Bounding Box Highlighting.
4. Sentiment & Tone Polarity Analysis.
5. Composite Document Extractive Summarization.
"""

import pytest
from app.summarizer import (
    DocumentNaiveBayesClassifier,
    get_naive_bayes_classifier,
    identify_file_format_and_mime,
    generate_zero_duplication_highlights,
    analyze_document_tone,
    generate_document_summary,
)


def test_naive_bayes_laplace_smoothing_classification():
    """Tests Paper 7 Naive Bayes classification with Laplace smoothing (+1/+2)."""
    clf = get_naive_bayes_classifier()
    assert clf.total_docs_trained > 0
    assert len(clf.classes) >= 5

    # Test Financial document
    fin_text = "Tax invoice issued for commercial goods with GST and paid total amount of INR 12500 via bank transfer."
    fin_pred = clf.predict(fin_text)
    assert fin_pred["predicted_class"] == "Financial / Transactional"
    assert fin_pred["confidence"] > 0.40
    assert "invoice" in fin_pred["matched_keywords"]
    assert "gst" in fin_pred["matched_keywords"]

    # Posteriors must sum to ~1.0
    post_sum = sum(fin_pred["posteriors"].values())
    assert 0.99 <= post_sum <= 1.01

    # Test Academic document
    acad_text = "Final semester examination marksheet for student roll 104 with grade credits and cumulative cgpa degree."
    acad_pred = clf.predict(acad_text)
    assert acad_pred["predicted_class"] == "Academic / Educational"
    assert acad_pred["confidence"] > 0.40
    assert "marksheet" in acad_pred["matched_keywords"]


def test_custom_naive_bayes_training():
    """Tests Paper 7 TrainNaiveBayes function on custom dataset."""
    custom_dataset = [
        ("solar panel inverter voltage battery grid power wattage", "Renewable Energy"),
        ("cardiology echocardiogram heart rate ecg pulse blood pressure", "Cardiology"),
    ]
    custom_keywords = ["solar", "battery", "inverter", "heart", "ecg", "cardiology"]
    clf = DocumentNaiveBayesClassifier(keywords=custom_keywords)
    clf.train(custom_dataset)

    res_solar = clf.predict("solar power battery backup system")
    assert res_solar["predicted_class"] == "Renewable Energy"

    res_heart = clf.predict("patient heart ecg checkup")
    assert res_heart["predicted_class"] == "Cardiology"


def test_deep_magic_byte_format_sniffer():
    """Tests Paper 7 Multi-Format identification using raw binary headers across 11 formats."""
    # 1. PDF
    pdf_bytes = b"%PDF-1.7\r\n\x25\xe2\xe3\xcf\xd3\r\n1 0 obj"
    pdf_info = identify_file_format_and_mime(pdf_bytes, filename="document.pdf")
    assert pdf_info["detected_format"] == "pdf"
    assert pdf_info["mime_type"] == "application/pdf"
    assert pdf_info["magic_byte_verified"] is True
    assert pdf_info["is_ocr_scannable"] is True

    # 2. JPEG
    jpeg_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01"
    jpeg_info = identify_file_format_and_mime(jpeg_bytes, filename="receipt.jpg")
    assert jpeg_info["detected_format"] == "jpg"
    assert jpeg_info["mime_type"] == "image/jpeg"
    assert jpeg_info["magic_byte_verified"] is True

    # 3. PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    png_info = identify_file_format_and_mime(png_bytes, filename="scan.png")
    assert png_info["detected_format"] == "png"
    assert png_info["mime_type"] == "image/png"

    # 4. TIFF (Little-Endian)
    tiff_bytes = b"II*\x00\x08\x00\x00\x00"
    tiff_info = identify_file_format_and_mime(tiff_bytes, filename="invoice.tiff")
    assert tiff_info["detected_format"] == "tiff"
    assert tiff_info["mime_type"] == "image/tiff"

    # 5. OpenXML DOCX (ZIP with word/ directory)
    docx_bytes = b"PK\x03\x04\x14\x00\x06\x00word/document.xml"
    docx_info = identify_file_format_and_mime(docx_bytes, filename="contract.docx")
    assert docx_info["detected_format"] == "docx"
    assert "wordprocessingml" in docx_info["mime_type"]

    # 6. Plain Text
    txt_bytes = "Simple plain text document containing notes and instructions.".encode("utf-8")
    txt_info = identify_file_format_and_mime(txt_bytes, filename="notes.txt")
    assert txt_info["detected_format"] == "txt"
    assert txt_info["mime_type"] == "text/plain"


def test_zero_duplication_highlighting():
    """Tests Paper 7 Zero-Duplication in-memory highlight generation."""
    sample_text = (
        "Tata Power Electricity Supply Bill. Customer Account Number 987654. "
        "Total billing amount payable is INR 4350. Please pay before due date."
    )
    ocr_boxes = [
        {"text": "Total", "ymin": 100, "xmin": 50, "ymax": 120, "xmax": 90},
        {"text": "billing", "ymin": 100, "xmin": 95, "ymax": 120, "xmax": 140},
        {"text": "amount", "ymin": 100, "xmin": 145, "ymax": 120, "xmax": 195},
    ]

    res = generate_zero_duplication_highlights(
        text=sample_text,
        search_query="Total billing",
        ocr_boxes=ocr_boxes,
        sample_file_size_kb=450.0,
    )

    assert res["match_count"] >= 1
    assert "<mark>" in res["html_snippet"]
    assert "</mark>" in res["html_snippet"]
    assert len(res["visual_bounding_boxes"]) >= 1
    assert res["storage_waste_prevented_kb"] == 450.0
    assert "Zero-Duplication" in res["architecture"]


def test_tone_and_urgency_polarity():
    """Tests Paper 7 Tone & Sentiment Polarity analysis."""
    urgent_text = "Final disconnection warning: payment of electricity bill is due immediately to avoid penalty and disconnection."
    tone_res = analyze_document_tone(urgent_text)
    assert tone_res["primary_tone"] in ("Urgent / Action Required", "Financial / Transactional")
    assert tone_res["urgency_level"] == "High / Immediate Attention"

    legal_text = "This legal agreement is entered into by the first party and second party with witness signatures under terms and conditions."
    legal_res = analyze_document_tone(legal_text)
    assert legal_res["primary_tone"] == "Legal / Contractual"


def test_composite_document_summary():
    """Tests Paper 7 & 8 composite document summarization."""
    invoice_text = (
        "OFFICIAL TAX INVOICE\n"
        "Reliance Digital Retail Limited, Lower Parel, Mumbai.\n"
        "Customer Name: Rahul Sharma, Contact: 9876543210.\n"
        "Invoice Number: INV-2026-9921, Date: 2026-10-25.\n"
        "Purchased 1x Apple MacBook Pro M3 Laptop.\n"
        "Subtotal amount is INR 1,69,900 with CGST 9% and SGST 9%.\n"
        "Grand total amount paid in full: INR 2,00,482.\n"
        "Thank you for shopping with Reliance Digital."
    )

    summary = generate_document_summary(
        text=invoice_text,
        max_bullets=3,
        filename="macbook_invoice.pdf",
    )

    assert len(summary["abstract"]) > 20
    assert len(summary["key_highlights"]) > 0
    assert summary["naive_bayes_classification"]["predicted_class"] == "Financial / Transactional"
    assert summary["tone_analysis"]["primary_tone"] == "Financial / Transactional"
    assert summary["file_format_metadata"]["detected_format"] == "pdf"
    assert summary["total_words"] > 20
