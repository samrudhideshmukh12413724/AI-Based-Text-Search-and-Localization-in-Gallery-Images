"""Synthetic Identity & Aadhaar-like Document Generator for Multi-Modal AI Benchmark.
Generates 25 highly diverse documents with mock identity cards, fictional profiles,
synthetic watermarks, varied positions, scales, orientations, and layout styles.
Zero real personal or government data used.
"""

import io
import json
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR.parent / "dataset" / "synthetic_ids"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# List of 25 fictional student/applicant profiles
PROFILES = [
    {"name": "Aarav Sharma", "dob": "15/05/2004", "gender": "Male", "dept": "Computer Science", "id_num": "4821 9012 3456", "city": "Pune"},
    {"name": "Priya Patel", "dob": "22/09/2003", "gender": "Female", "dept": "Information Tech", "id_num": "5912 8841 0023", "city": "Ahmedabad"},
    {"name": "Sneha Kulkarni", "dob": "11/12/2004", "gender": "Female", "dept": "Mechanical Eng", "id_num": "3104 5592 1198", "city": "Nashik"},
    {"name": "Arjun Reddy", "dob": "03/04/2003", "gender": "Male", "dept": "Electrical Eng", "id_num": "7719 3302 4410", "city": "Hyderabad"},
    {"name": "Ananya Iyer", "dob": "19/08/2004", "gender": "Female", "dept": "Civil Engineering", "id_num": "6640 1290 8831", "city": "Chennai"},
    {"name": "Kavita Nair", "dob": "27/01/2004", "gender": "Female", "dept": "Biotechnology", "id_num": "4490 6612 7743", "city": "Bengaluru"},
    {"name": "Rahul Verma", "dob": "08/11/2003", "gender": "Male", "dept": "Chemical Eng", "id_num": "8812 4430 9901", "city": "Delhi"},
    {"name": "Neha Gupta", "dob": "14/06/2004", "gender": "Female", "dept": "Artificial Intell", "id_num": "2291 7703 5519", "city": "Lucknow"},
    {"name": "Aditya Joshi", "dob": "30/03/2004", "gender": "Male", "dept": "Data Science", "id_num": "9930 1148 2274", "city": "Mumbai"},
    {"name": "Meera Sen", "dob": "05/07/2003", "gender": "Female", "dept": "Electronics & Comm", "id_num": "3381 6690 4425", "city": "Kolkata"},
    {"name": "Rohan Deshpande", "dob": "18/02/2004", "gender": "Male", "dept": "Robotics & Auto", "id_num": "5510 9923 8840", "city": "Nagpur"},
    {"name": "Tanvi Bhatia", "dob": "25/10/2004", "gender": "Female", "dept": "Cyber Security", "id_num": "1189 4402 7731", "city": "Chandigarh"},
    {"name": "Vikram Rathore", "dob": "09/09/2003", "gender": "Male", "dept": "Aerospace Eng", "id_num": "7720 3381 5590", "city": "Jaipur"},
    {"name": "Ishaan Mukherjee", "dob": "12/04/2004", "gender": "Male", "dept": "Software Systems", "id_num": "6631 8890 2214", "city": "Bhopal"},
    {"name": "Divya Menon", "dob": "21/08/2004", "gender": "Female", "dept": "Applied Math", "id_num": "4410 7723 9980", "city": "Kochi"},
    {"name": "Karan Malhotra", "dob": "17/03/2003", "gender": "Male", "dept": "Business Analytics", "id_num": "8839 2201 6645", "city": "Gurugram"},
    {"name": "Pooja Hegde", "dob": "29/11/2004", "gender": "Female", "dept": "Cloud Computing", "id_num": "5502 9918 3374", "city": "Mangaluru"},
    {"name": "Siddharth Rao", "dob": "04/01/2004", "gender": "Male", "dept": "VLSI Design", "id_num": "3391 8840 5521", "city": "Mysuru"},
    {"name": "Aniket Shinde", "dob": "16/05/2004", "gender": "Male", "dept": "Mechatronics", "id_num": "9921 4470 1183", "city": "Kolhapur"},
    {"name": "Ritu Singhania", "dob": "23/07/2003", "gender": "Female", "dept": "Petroleum Eng", "id_num": "2280 6631 7794", "city": "Dehradun"},
    {"name": "Varun Chawla", "dob": "02/12/2003", "gender": "Male", "dept": "Financial Tech", "id_num": "7741 5509 8820", "city": "Indore"},
    {"name": "Deepika Das", "dob": "13/09/2004", "gender": "Female", "dept": "Genetics & Health", "id_num": "6690 3312 4481", "city": "Guwahati"},
    {"name": "Manish Tiwari", "dob": "28/06/2004", "gender": "Male", "dept": "Renewable Energy", "id_num": "1140 8892 5537", "city": "Varanasi"},
    {"name": "Shreya Pillai", "dob": "07/10/2003", "gender": "Female", "dept": "Nanotechnology", "id_num": "5581 2240 9913", "city": "Thiruvananthapuram"},
    {"name": "Gaurav Choudhury", "dob": "19/04/2004", "gender": "Male", "dept": "Nuclear Science", "id_num": "3309 7718 6642", "city": "Bhubaneswar"},
]

def draw_avatar_photo(draw, px, py, pw, ph, is_female=False):
    draw.rectangle([px, py, px + pw, py + ph], fill=(230, 238, 248), outline=(100, 115, 135), width=2)
    cx = px + pw // 2
    cy = py + ph // 2 - 8
    # Head
    head_r = min(pw, ph) // 4
    draw.ellipse([cx - head_r, cy - head_r - 5, cx + head_r, cy + head_r - 5], fill=(245, 205, 185), outline=(160, 120, 100), width=2)
    # Hair
    hair_color = (30, 20, 15) if is_female else (40, 30, 25)
    draw.arc([cx - head_r - 2, cy - head_r - 8, cx + head_r + 2, cy + head_r // 2], start=180, end=360, fill=hair_color, width=4)
    # Torso
    torso_color = (20, 90, 170) if is_female else (30, 120, 70)
    draw.ellipse([cx - head_r * 1.6, cy + head_r + 5, cx + head_r * 1.6, py + ph + 25], fill=torso_color)
    draw.text((px + 10, py + ph - 18), "[ID Photo]", fill=(80, 80, 80))

def draw_mock_aadhaar_card(draw, x, y, w, h, p, style="standard"):
    # Outer Card Border
    bg_color = (255, 255, 255) if style != "faded" else (248, 246, 240)
    border_color = (120, 135, 155) if style != "faded" else (160, 165, 170)
    draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=border_color, width=3)

    # Tricolor Header Bar
    strip_h = max(6, h // 30)
    draw.rectangle([x + 3, y + 3, x + w - 3, y + 3 + strip_h], fill=(255, 153, 51))
    draw.rectangle([x + 3, y + 3 + strip_h, x + w - 3, y + 3 + strip_h * 2], fill=(255, 255, 255))
    draw.rectangle([x + 3, y + 3 + strip_h * 2, x + w - 3, y + 3 + strip_h * 3], fill=(19, 136, 8))

    # Watermark overlay
    draw.text((x + 25, y + strip_h * 3 + 6), "SYNTHETIC SAMPLE FOR AI BENCHMARK", fill=(210, 215, 225))

    # Card Title
    draw.text((x + 25, y + 35), "GOVERNMENT OF INDIA", fill=(0, 0, 0))
    draw.text((x + 25, y + 55), "Unique Identification Authority of India", fill=(70, 70, 70))
    draw.text((x + w - 190, y + 35), "AADHAAR CARD", fill=(180, 10, 10))
    draw.line([x + 15, y + 78, x + w - 15, y + 78], fill=(190, 200, 215), width=2)

    # Photo Box
    pw = int(w * 0.22)
    ph = int(h * 0.42)
    px = x + 25
    py = y + 95
    is_fem = (p["gender"] == "Female")
    draw_avatar_photo(draw, px, py, pw, ph, is_female=is_fem)

    # Profile Text Info
    tx = px + pw + 25
    ty = y + 95
    draw.text((tx, ty), f"Name: {p['name']}", fill=(10, 10, 10))
    draw.text((tx, ty + 24), f"DOB: {p['dob']}", fill=(10, 10, 10))
    draw.text((tx, ty + 48), f"Gender: {p['gender']}", fill=(10, 10, 10))
    draw.text((tx, ty + 72), f"Address: {p['city']}, India", fill=(50, 50, 50))

    # 12-digit Number Box
    box_y = ty + 105
    draw.rectangle([tx - 5, box_y, x + w - 25, box_y + 40], fill=(245, 248, 255), outline=(170, 190, 220), width=1)
    draw.text((tx + 15, box_y + 10), p["id_num"], fill=(170, 20, 20))

    # Footer Banner
    draw.rectangle([x + 3, y + h - 35, x + w - 3, y + h - 3], fill=(235, 242, 250))
    draw.text((x + int(w * 0.18), y + h - 26), "MERA AADHAAR, MERI PEHCHAN -- AADHAAR CARD", fill=(20, 40, 90))

def draw_mock_student_id_card(draw, x, y, w, h, p, orientation="landscape"):
    draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255), outline=(30, 60, 120), width=3)
    header_h = 55
    draw.rectangle([x + 3, y + 3, x + w - 3, y + header_h], fill=(20, 50, 110))
    draw.text((x + 20, y + 15), "APEX UNIVERSITY -- STUDENT IDENTITY CARD", fill=(255, 255, 255))
    draw.text((x + 20, y + 35), "OFFICIAL CAMPUS IDENTITY PROOF", fill=(220, 235, 255))

    pw = int(w * 0.24)
    ph = int(h * 0.44)
    px = x + w - pw - 25
    py = y + header_h + 20
    is_fem = (p["gender"] == "Female")
    draw_avatar_photo(draw, px, py, pw, ph, is_female=is_fem)

    tx = x + 25
    ty = y + header_h + 20
    draw.text((tx, ty), f"Student: {p['name']}", fill=(10, 10, 10))
    draw.text((tx, ty + 25), f"Dept: {p['dept']}", fill=(10, 10, 10))
    draw.text((tx, ty + 50), f"Roll No: APEX-2024-{random.randint(1000, 9999)}", fill=(10, 10, 10))
    draw.text((tx, ty + 75), "Card Type: STUDENT ID CARD PROOF", fill=(180, 20, 20))
    draw.text((tx, ty + 100), f"Validity: 2024 - 2028 | Blood: O+", fill=(60, 60, 60))

    # Barcode representation
    bc_x = tx
    bc_y = ty + 130
    for b in range(0, 180, 6):
        bw = random.choice([2, 3, 4])
        draw.line([bc_x + b, bc_y, bc_x + b, bc_y + 25], fill=(0, 0, 0), width=bw)

    draw.rectangle([x + 3, y + h - 30, x + w - 3, y + h - 3], fill=(230, 238, 250))
    draw.text((x + 25, y + h - 22), "SYNTHETIC SAMPLE FOR AI BENCHMARK -- NOT REAL ID", fill=(70, 80, 100))


def generate_all_synthetic_ids():
    print("=" * 90)
    print("GENERATING 25 DIVERSE SYNTHETIC ID & AADHAAR BENCHMARK DOCUMENTS")
    print("=" * 90)

    ground_truth = {}

    for idx, profile in enumerate(PROFILES, 1):
        file_name = f"doc_synth_id_{idx:02d}.jpg"
        doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
        draw = ImageDraw.Draw(doc)

        # Draw formal outer border
        draw.rectangle([25, 25, 875, 1175], outline=(180, 190, 205), width=2)

        # Header Title
        draw.text((120, 50), "APEX UNIVERSITY CENTRAL ADMISSIONS & VERIFICATION", fill=(15, 30, 80))
        draw.line([50, 90, 850, 90], fill=(20, 45, 95), width=2)

        # Document Variation Routing
        is_aadhaar_type = (idx % 2 != 0)  # Odd = Aadhaar style, Even = Student ID style
        pos_variant = (idx % 5)           # 5 distinct spatial positions

        # Text prompt referencing the enclosure
        if is_aadhaar_type:
            doc_title = "GOVERNMENT SCHOLARSHIP IDENTITY ATTACHMENT FORM"
            prompt_text = "Mandatory: Please attach Aadhaar Card photocopy below for identity verification."
            target_label = "Aadhaar Card Enclosure"
            search_query_target = "Aadhaar"
        else:
            doc_title = "ANNUAL COURSE REGISTRATION & IDENTITY ENDORSEMENT"
            prompt_text = "Enclosure Required: Student Identity Card (ID Card) copy verified by department."
            target_label = "Student ID Card Enclosure"
            search_query_target = "Student ID Card"

        draw.text((150, 120), doc_title, fill=(180, 25, 25))
        draw.text((50, 165), f"Applicant / Student: {profile['name']}", fill=(0, 0, 0))
        draw.text((50, 195), f"Program: Bachelor of Technology ({profile['dept']})", fill=(0, 0, 0))
        draw.text((50, 225), f"Application Ref: AIT-2026-VERIF-{random.randint(10000, 99999)}", fill=(0, 0, 0))
        draw.text((50, 265), prompt_text, fill=(15, 15, 15))

        # Position Variations:
        # Pos 0: Middle-Center (Standard 720x400)
        # Pos 1: Lower-Center (720x420 at y=600)
        # Pos 2: Left-Aligned Mid (650x380 at x=60)
        # Pos 3: Right-Aligned Mid (650x380 at x=190)
        # Pos 4: Compact Upper Attachment (600x340 at y=320)
        if pos_variant == 0:
            bx, by, bw, bh = 90, 340, 720, 400
            loc_desc = "Center"
        elif pos_variant == 1:
            bx, by, bw, bh = 90, 520, 720, 420
            loc_desc = "Bottom-Center"
        elif pos_variant == 2:
            bx, by, bw, bh = 60, 360, 680, 390
            loc_desc = "Middle-Left"
        elif pos_variant == 3:
            bx, by, bw, bh = 160, 360, 680, 390
            loc_desc = "Middle-Right"
        else:
            bx, by, bw, bh = 140, 320, 620, 360
            loc_desc = "Top-Center"

        # Quality variations (Faded scan on idx 13, 21)
        style = "faded" if idx in (13, 21) else "standard"

        # Draw the embedded Card
        if is_aadhaar_type:
            draw_mock_aadhaar_card(draw, bx, by, bw, bh, profile, style=style)
        else:
            draw_mock_student_id_card(draw, bx, by, bw, bh, profile)

        # Footer Verification and Signature Section
        sig_y = min(1000, by + bh + 40)
        draw.text((50, sig_y), "DECLARATION:", fill=(50, 50, 50))
        draw.text((50, sig_y + 25), "I hereby confirm the attached identity card document copy is authentic.", fill=(80, 80, 80))
        draw.text((50, sig_y + 60), f"Date: 0{idx % 28 + 1}-Feb-2026 | Location: {profile['city']}", fill=(60, 60, 60))

        # Registrar / Student Signature box at bottom right
        draw.text((600, sig_y + 60), "Authorized Signature", fill=(80, 80, 80))
        draw.line([580, sig_y + 55, 830, sig_y + 55], fill=(160, 170, 180), width=1)

        # Slight Gaussian Blur for scan realism on specific documents
        if idx in (7, 19):
            doc = doc.filter(ImageFilter.GaussianBlur(radius=0.6))

        save_path = OUTPUT_DIR / file_name
        doc.save(save_path, quality=94)

        # Record Ground Truth Metadata
        ground_truth[file_name] = {
            "query_target": search_query_target,
            "profile_name": profile["name"],
            "category": "SYNTHETIC_ID",
            "is_aadhaar_type": is_aadhaar_type,
            "has_text_match": True,
            "has_visual_match": True,
            "visual_target": target_label,
            "location_desc": loc_desc,
            "bbox": {"x": bx, "y": by, "width": bw, "height": bh},
            "normalized_bbox": {
                "x": round(bx / 900, 4),
                "y": round(by / 1200, 4),
                "width": round(bw / 900, 4),
                "height": round(bh / 1200, 4)
            }
        }
        print(f"  [{idx:02d}/25] Generated {file_name} | Type: {target_label} | Loc: {loc_desc} | Person: {profile['name']}")

    # Save Ground Truth JSON
    gt_file = OUTPUT_DIR / "ground_truth_synthetic_ids.json"
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nSuccessfully generated 25 diverse synthetic ID documents in {OUTPUT_DIR}")
    print(f"Ground truth saved to: {gt_file.name}")
    print("=" * 90)

if __name__ == "__main__":
    generate_all_synthetic_ids()
