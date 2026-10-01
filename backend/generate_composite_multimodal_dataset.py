"""Generates realistic composite multi-modal benchmark documents:
1. doc_composite_01_aadhaar.jpg: Scholarship Application with student Samrudhi Deshmukh, OCR text "Please attach Aadhaar Card", embedded realistic Aadhaar card image, and signature.
2. doc_composite_02_student_id.jpg: Registration Form with "Official student identity proof", embedded Student ID Card, photo, and official seal.
3. doc_composite_03_text_control.jpg: Negative visual control with text only.
"""

import io
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
DATASET_DIR = ROOT_DIR.parent / "dataset" / "composite"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# Helper for drawing cursive blue signature
def draw_signature(draw, start_x, start_y, width, height, stroke_color=(20, 50, 160)):
    points = []
    cx = start_x + 20
    cy = start_y + height // 2 + 10
    for t in range(0, 180, 2):
        rad = math.radians(t * 3.8)
        px = cx + t * 1.1 + math.sin(rad * 2.2) * 16
        py = cy + math.sin(rad * 4.5) * 22 + math.cos(rad * 1.5) * 10
        points.append((px, py))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=stroke_color, width=3)
    # Underline swirl
    draw.arc([start_x + 10, start_y + height - 25, start_x + width - 20, start_y + height - 5], start=160, end=350, fill=stroke_color, width=3)

# Helper for drawing realistic Aadhaar card graphic enclosure
def draw_aadhaar_card(draw, base_img, x, y, w, h):
    # Card outer rounded rectangle with drop-shadow border
    card_bg = (255, 255, 255)
    draw.rectangle([x, y, x + w, y + h], fill=card_bg, outline=(140, 150, 165), width=3)

    # Tricolor top header strip (Saffron, White, Green)
    strip_h = 14
    draw.rectangle([x + 3, y + 3, x + w - 3, y + 3 + strip_h], fill=(255, 153, 51))
    draw.rectangle([x + 3, y + 3 + strip_h, x + w - 3, y + 3 + strip_h * 2], fill=(255, 255, 255))
    draw.rectangle([x + 3, y + 3 + strip_h * 2, x + w - 3, y + 3 + strip_h * 3], fill=(19, 136, 8))

    # Header text
    draw.text((x + 80, y + 55), "GOVERNMENT OF INDIA", fill=(0, 0, 0))
    draw.text((x + 80, y + 75), "Unique Identification Authority of India", fill=(70, 70, 70))
    draw.text((x + w - 240, y + 55), "AADHAAR CARD", fill=(180, 0, 0))
    draw.line([x + 20, y + 105, x + w - 20, y + 105], fill=(200, 200, 200), width=2)

    # Student Portrait Photograph box inside card
    photo_x = x + 35
    photo_y = y + 125
    photo_w = 130
    photo_h = 160
    draw.rectangle([photo_x, photo_y, photo_x + photo_w, photo_y + photo_h], fill=(225, 235, 245), outline=(90, 100, 120), width=2)
    # Draw simple avatar portrait
    head_cx = photo_x + photo_w // 2
    head_cy = photo_y + 60
    draw.ellipse([head_cx - 30, head_cy - 35, head_cx + 30, head_cy + 35], fill=(240, 200, 180), outline=(150, 110, 90), width=2)
    draw.ellipse([head_cx - 45, photo_y + 115, head_cx + 45, photo_y + 195], fill=(30, 80, 160))
    draw.text((photo_x + 18, photo_y + photo_h - 22), "[Photo Attached]", fill=(60, 60, 60))

    # Card textual data fields
    text_x = photo_x + photo_w + 35
    text_y = y + 125
    draw.text((text_x, text_y), "Name: Samrudhi Deshmukh", fill=(10, 10, 10))
    draw.text((text_x, text_y + 30), "DOB: 14/08/2004", fill=(10, 10, 10))
    draw.text((text_x, text_y + 60), "Gender: Female / stree", fill=(10, 10, 10))
    draw.text((text_x, text_y + 90), "Address: Pune, Maharashtra, 411038", fill=(50, 50, 50))

    # Big 12-digit Aadhaar Number
    draw.rectangle([text_x - 5, text_y + 125, x + w - 40, text_y + 175], fill=(245, 248, 255), outline=(180, 200, 230), width=1)
    draw.text((text_x + 20, text_y + 138), "4829  1048  9301", fill=(160, 10, 10))

    # Bottom Footer Bar (Mera Aadhaar, Meri Pehchan)
    draw.rectangle([x + 3, y + h - 45, x + w - 3, y + h - 3], fill=(235, 240, 248))
    draw.text((x + 130, y + h - 35), "MERA AADHAAR, MERI PEHCHAN  --  AADHAAR CARD", fill=(20, 40, 90))

# Helper for drawing Student ID Card enclosure
def draw_student_id_card(draw, base_img, x, y, w, h):
    # Card outer rectangle
    draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255), outline=(50, 80, 130), width=3)
    # Header banner
    draw.rectangle([x + 3, y + 3, x + w - 3, y + 65], fill=(20, 50, 110))
    draw.text((x + 120, y + 20), "APEX UNIVERSITY -- STUDENT IDENTITY CARD", fill=(255, 255, 255))

    # Photo box at right
    photo_x = x + w - 170
    photo_y = y + 85
    photo_w = 135
    photo_h = 165
    draw.rectangle([photo_x, photo_y, photo_x + photo_w, photo_y + photo_h], fill=(230, 240, 250), outline=(80, 100, 130), width=2)
    # Draw avatar portrait
    head_cx = photo_x + photo_w // 2
    head_cy = photo_y + 60
    draw.ellipse([head_cx - 28, head_cy - 35, head_cx + 28, head_cy + 35], fill=(240, 200, 180), outline=(150, 110, 90), width=2)
    draw.ellipse([head_cx - 42, photo_y + 115, head_cx + 42, photo_y + 195], fill=(20, 120, 80))
    draw.text((photo_x + 25, photo_y + photo_h - 22), "[ID Photo]", fill=(40, 40, 40))

    # Student Details
    text_x = x + 35
    text_y = y + 90
    draw.text((text_x, text_y), "Student Name: Rohan V. Sharma", fill=(10, 10, 10))
    draw.text((text_x, text_y + 32), "Course: B.Tech Computer Engineering", fill=(10, 10, 10))
    draw.text((text_x, text_y + 64), "Roll No: CS-2026-88192", fill=(10, 10, 10))
    draw.text((text_x, text_y + 96), "Validity: 2024 - 2028 | Blood: B+", fill=(10, 10, 10))
    draw.text((text_x, text_y + 128), "Identity Proof Type: COLLEGE ID PROOF", fill=(180, 20, 20))

    # Bottom Bar
    draw.rectangle([x + 3, y + h - 45, x + w - 3, y + h - 3], fill=(230, 235, 245))
    draw.text((x + 140, y + h - 35), "AUTHORISED IDENTITY CARD -- APEX EDUCATION", fill=(30, 60, 120))


def generate_documents():
    print("=" * 80)
    print("GENERATING COMPOSITE MULTI-MODAL BENCHMARK DATASET")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Document 1: Application Form with Samrudhi, Aadhaar Card + Signature
    # -------------------------------------------------------------------------
    doc1 = Image.new("RGB", (900, 1200), color=(255, 255, 255))
    draw1 = ImageDraw.Draw(doc1)

    # Outer border
    draw1.rectangle([25, 25, 875, 1175], outline=(180, 190, 200), width=2)

    # Header
    draw1.text((120, 50), "APEX INSTITUTE OF HIGHER EDUCATION & RESEARCH", fill=(10, 30, 80))
    draw1.text((180, 80), "OFFICE OF SCHOLARSHIPS & STUDENT AID", fill=(70, 70, 70))
    draw1.line([50, 115, 850, 115], fill=(30, 50, 100), width=3)

    # Form title
    draw1.text((160, 140), "SCHOLARSHIP VERIFICATION APPLICATION FORM", fill=(180, 20, 20))
    draw1.text((50, 185), "Applicant Name: Samrudhi Deshmukh", fill=(0, 0, 0))
    draw1.text((50, 215), "Application Number: AIT-2026-SCH-9042", fill=(0, 0, 0))
    draw1.text((50, 245), "Academic Program: Bachelor of Technology (Computer Science)", fill=(0, 0, 0))
    draw1.text((50, 275), "Category: Merit-Cum-Means State Scholarship Grant", fill=(0, 0, 0))

    # Explicit instruction text mentioning Aadhaar Card
    draw1.text((50, 330), "MANDATORY REQUIREMENT:", fill=(160, 0, 0))
    draw1.text((50, 360), "Please attach Aadhaar Card copy below for biometric identity verification.", fill=(10, 10, 10))

    # Embedded Aadhaar Card Enclosure (at middle-page: x=90, y=410, w=720, h=420)
    aadhaar_box = {"x": 90, "y": 410, "width": 720, "height": 420}
    draw_aadhaar_card(draw1, doc1, aadhaar_box["x"], aadhaar_box["y"], aadhaar_box["width"], aadhaar_box["height"])

    # Bottom Declaration & Signature Section
    draw1.text((50, 870), "DECLARATION OF APPLICANT:", fill=(30, 30, 30))
    draw1.text((50, 900), "I hereby confirm that the attached Aadhaar card details and document records", fill=(60, 60, 60))
    draw1.text((50, 925), "are true to the best of my knowledge and verified by the institute.", fill=(60, 60, 60))

    draw1.text((50, 990), "Date: 12-Feb-2026", fill=(40, 40, 40))
    draw1.text((50, 1020), "Place: Pune, Maharashtra", fill=(40, 40, 40))

    # Signature box at bottom-right
    sign_box = {"x": 580, "y": 960, "width": 260, "height": 130}
    draw1.rectangle([sign_box["x"], sign_box["y"], sign_box["x"] + sign_box["width"], sign_box["y"] + sign_box["height"]], outline=(200, 200, 210), width=1)
    draw_signature(draw1, sign_box["x"], sign_box["y"], sign_box["width"], sign_box["height"])
    draw1.text((sign_box["x"] + 35, sign_box["y"] + sign_box["height"] - 20), "Applicant Signature", fill=(80, 80, 80))

    path1 = DATASET_DIR / "doc_composite_01_aadhaar.jpg"
    doc1.save(path1, quality=95)
    print(f"  [Created] {path1.name} (Contains Text 'Aadhaar Card' + Embedded Aadhaar Card Image + Signature)")

    # -------------------------------------------------------------------------
    # Document 2: Registration Form with Student ID Card + Stamp
    # -------------------------------------------------------------------------
    doc2 = Image.new("RGB", (900, 1200), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(doc2)
    draw2.rectangle([25, 25, 875, 1175], outline=(180, 190, 200), width=2)

    draw2.text((160, 50), "APEX UNIVERSITY CENTRAL ADMISSIONS OFFICE", fill=(10, 30, 80))
    draw2.line([50, 100, 850, 100], fill=(30, 50, 100), width=2)

    draw2.text((180, 130), "SEMESTER COURSE REGISTRATION ENDORSEMENT", fill=(160, 20, 20))
    draw2.text((50, 180), "Student Registration Record: Rohan V. Sharma", fill=(0, 0, 0))
    draw2.text((50, 215), "Official student identity proof required for entrance and laboratory access.", fill=(0, 0, 0))
    draw2.text((50, 250), "Enclosure verified: Student Identity Card (ID Card) attached below.", fill=(30, 30, 30))

    # Embedded Student ID Card (x=90, y=320, w=720, h=400)
    id_box = {"x": 90, "y": 320, "width": 720, "height": 400}
    draw_student_id_card(draw2, doc2, id_box["x"], id_box["y"], id_box["width"], id_box["height"])

    # Stamp at bottom-left
    stamp_cx, stamp_cy = 200, 950
    draw2.ellipse([stamp_cx - 70, stamp_cy - 70, stamp_cx + 70, stamp_cy + 70], outline=(180, 20, 20), width=3)
    draw2.ellipse([stamp_cx - 58, stamp_cy - 58, stamp_cx + 58, stamp_cy + 58], outline=(180, 20, 20), width=1)
    draw2.text((stamp_cx - 42, stamp_cy - 10), "VERIFIED", fill=(180, 20, 20))
    draw2.text((stamp_cx - 48, stamp_cy + 15), "REGISTRAR", fill=(180, 20, 20))

    # Registrar Signature at bottom-right
    sign2_box = {"x": 580, "y": 920, "width": 260, "height": 130}
    draw_signature(draw2, sign2_box["x"], sign2_box["y"], sign2_box["width"], sign2_box["height"], stroke_color=(10, 40, 120))
    draw2.text((sign2_box["x"] + 35, sign2_box["y"] + sign2_box["height"] - 15), "Registrar Signature", fill=(80, 80, 80))

    path2 = DATASET_DIR / "doc_composite_02_student_id.jpg"
    doc2.save(path2, quality=95)
    print(f"  [Created] {path2.name} (Contains Text 'identity proof' + Embedded Student ID Card + Stamp)")

    # -------------------------------------------------------------------------
    # Document 3: Text-Only Negative Visual Control
    # -------------------------------------------------------------------------
    doc3 = Image.new("RGB", (900, 1200), color=(255, 255, 255))
    draw3 = ImageDraw.Draw(doc3)
    draw3.rectangle([25, 25, 875, 1175], outline=(180, 190, 200), width=2)

    draw3.text((150, 50), "APEX UNIVERSITY ACADEMIC COUNCIL CIRCULAR", fill=(10, 30, 80))
    draw3.line([50, 100, 850, 100], fill=(30, 50, 100), width=2)
    draw3.text((160, 140), "ANNUAL ACADEMIC SYLLABUS & EVALUATION RULES", fill=(20, 20, 20))

    lines = [
        "1. All enrolled undergraduate students must complete minimum 75% attendance.",
        "2. Continuous internal assessment comprises class quizzes, laboratory reports, and midterms.",
        "3. Semester end examinations will be held in offline mode across allocated university halls.",
        "4. Students are advised to consult their faculty mentors for elective course registrations.",
        "5. Grading policy follows standard 10-point cumulative grade point average (CGPA) scheme.",
        "6. Late submissions of laboratory journals are subject to penalty marks deduction.",
        "7. Re-evaluation requests must be submitted within 14 calendar days of results announcement."
    ]
    y_pos = 220
    for line in lines:
        draw3.text((60, y_pos), line, fill=(30, 30, 30))
        y_pos += 65

    path3 = DATASET_DIR / "doc_composite_03_text_control.jpg"
    doc3.save(path3, quality=95)
    print(f"  [Created] {path3.name} (Clean text-only control document)")

    # Ground truth metadata
    gt_file = DATASET_DIR / "ground_truth_composite.json"
    gt = {
        "doc_composite_01_aadhaar.jpg": {
            "query_target": "Aadhaar",
            "has_text_match": True,
            "text_terms": ["Aadhaar Card", "Samrudhi Deshmukh", "Scholarship"],
            "has_visual_match": True,
            "visual_target": "Aadhaar Card Enclosure",
            "bbox": aadhaar_box,
            "signature_bbox": sign_box
        },
        "doc_composite_02_student_id.jpg": {
            "query_target": "Student ID Card",
            "has_text_match": True,
            "text_terms": ["identity proof", "Student Identity Card"],
            "has_visual_match": True,
            "visual_target": "Student ID Card Enclosure",
            "bbox": id_box
        },
        "doc_composite_03_text_control.jpg": {
            "has_text_match": False,
            "has_visual_match": False
        }
    }
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)
    print(f"  [Created] {gt_file.name}")
    print("=" * 80)

if __name__ == "__main__":
    generate_documents()
