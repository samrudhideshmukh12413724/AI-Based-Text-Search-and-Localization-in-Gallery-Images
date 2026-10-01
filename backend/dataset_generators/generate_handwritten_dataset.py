"""Handwritten Document Generator for Multi-Modal AI Benchmark.
Generates 25 realistic, varied handwritten document images with cursive script simulations,
ink variations (blue/black/grey), ruled and unruled paper textures, margin lines,
and diverse student administrative scenarios (leave requests, re-evaluations, extensions).
"""

import io
import json
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR.parent / "dataset" / "handwritten"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TOPICS = [
    {"subject": "Application for Sick Leave", "text": "Respected Sir, I am suffering from viral fever and request 3 days medical leave from classes.", "student": "Aarav Sharma", "roll": "CS-2024-101"},
    {"subject": "Request for Exam Re-evaluation", "text": "Dear Controller of Exams, I request re-checking of my Data Structures paper for question 4 marks.", "student": "Priya Patel", "roll": "IT-2024-102"},
    {"subject": "Hostel Late Night Pass", "text": "Respected Warden, Please grant permission to return to hostel at 10 PM for project group work.", "student": "Sneha Kulkarni", "roll": "ME-2024-103"},
    {"subject": "Library Overdue Book Waiver", "text": "To Librarian, Kindly waive the fine on operating systems textbook as I was hospitalized.", "student": "Arjun Reddy", "roll": "EE-2024-104"},
    {"subject": "Lab Equipment Requisition", "text": "Respected Faculty Incharge, Requesting issue of digital oscilloscope for mini-project testing.", "student": "Ananya Iyer", "roll": "CV-2024-105"},
    {"subject": "Project Extension Submission", "text": "Dear Professor, Due to hardware component delivery delay, requesting 5 days extension for final code.", "student": "Kavita Nair", "roll": "BT-2024-106"},
    {"subject": "Duplicate Fee Receipt Appeal", "text": "Finance Office, I lost my original semester fee receipt and request an attested duplicate copy.", "student": "Rahul Verma", "roll": "CH-2024-107"},
    {"subject": "Bus Route Change Request", "text": "Transport Manager, I shifted residence to Kothrud and request transfer to bus route number 14.", "student": "Neha Gupta", "roll": "AI-2024-108"},
    {"subject": "Sports Equipment Issue Note", "text": "Sports Incharge, Requesting issue of 4 badminton racquets and shuttlecock box for practice.", "student": "Aditya Joshi", "roll": "DS-2024-109"},
    {"subject": "Cultural Fest Participation NoC", "text": "Dean Student Welfare, Kindly grant attendance concession for 2 days inter-collegiate drama contest.", "student": "Meera Sen", "roll": "EC-2024-110"},
    {"subject": "Hostel Room Shift Request", "text": "Warden, Requesting room shift to second floor due to water leakage issue in current room 104.", "student": "Rohan Deshpande", "roll": "RO-2024-111"},
    {"subject": "Bonafide Application for Passport", "text": "Registrar, Please issue a bonafide student certificate for my fresh passport verification process.", "student": "Tanvi Bhatia", "roll": "CY-2024-112"},
    {"subject": "Elective Subject Change", "text": "HOD, Requesting permission to change open elective from Cloud Security to Quantum Computing.", "student": "Vikram Rathore", "roll": "AE-2024-113"},
    {"subject": "Attendance Shortage Appeal", "text": "Academic Dean, Kindly consider my attendance shortage as I represented university in debate championship.", "student": "Ishaan Mukherjee", "roll": "SS-2024-114"},
    {"subject": "Internship No Objection Certificate", "text": "Placement Cell, Requesting NoC for 2 months summer internship at Infosys development center.", "student": "Divya Menon", "roll": "AM-2024-115"},
    {"subject": "Mess Food Quality Complaint", "text": "Mess Committee, Bringing to notice poor quality of dinner served on Monday and requesting inspection.", "student": "Karan Malhotra", "roll": "BA-2024-116"},
    {"subject": "Gymnasium Membership Slip", "text": "Sports Officer, Submitting registration form and medical clearance for evening gym batch access.", "student": "Pooja Hegde", "roll": "CC-2024-117"},
    {"subject": "ID Card Damaged Replacement", "text": "Campus Security, My student smart card is cracked and not detected by turnstiles. Requesting replacement.", "student": "Siddharth Rao", "roll": "VL-2024-118"},
    {"subject": "Seminar Hall Booking Form", "text": "Event Coordinator, Requesting booking of APJ Abdul Kalam auditorium for robotics workshop on Saturday.", "student": "Aniket Shinde", "roll": "MC-2024-119"},
    {"subject": "Scholarship Cheque Endorsement", "text": "Accounts Dept, Please endorse my state scholarship cheque for fee deposit adjustment.", "student": "Ritu Singhania", "roll": "PE-2024-120"},
    {"subject": "WiFi Login Reset Request", "text": "IT Helpdesk, My campus portal WiFi credentials are locked after password expiry. Kindly reset.", "student": "Varun Chawla", "roll": "FT-2024-121"},
    {"subject": "Medical Emergency Leave", "text": "Class Teacher, Applying for 4 days emergency leave due to immediate surgery of family member.", "student": "Deepika Das", "roll": "GH-2024-122"},
    {"subject": "Industrial Visit Exemption", "text": "Faculty Coordinator, Seeking exemption from Mumbai factory visit due to conflicting gate exam schedule.", "student": "Manish Tiwari", "roll": "RE-2024-123"},
    {"subject": "Hostel Caution Deposit Refund", "text": "Finance Office, I vacated hostel after semester completion. Please process caution deposit refund.", "student": "Shreya Pillai", "roll": "NT-2024-124"},
    {"subject": "Transcript Request Letter", "text": "Examination Cell, Requesting 3 sealed official transcript sets for higher studies abroad application.", "student": "Gaurav Choudhury", "roll": "NS-2024-125"},
]

def draw_ruled_lines(draw, W, H, line_spacing=42, start_y=160, end_y=1100):
    # Margin vertical red line
    draw.line([110, 40, 110, H - 40], fill=(230, 150, 150), width=2)
    # Horizontal blue ledger lines
    for y in range(start_y, end_y, line_spacing):
        draw.line([60, y, W - 60, y], fill=(210, 225, 245), width=1)

def draw_cursive_sentence(draw, text, start_x, start_y, ink_color, slant=1.1, word_spacing=18):
    words = text.split()
    curr_x = start_x
    for word in words:
        # Simulate handwritten word contour with connected undulating spline
        points = []
        w_len = len(word) * 14
        for step in range(0, int(w_len), 3):
            rad = math.radians(step * 4.2)
            px = curr_x + step * slant + math.sin(rad * 1.5) * 2.5
            py = start_y + math.sin(rad * 3.8) * 5 + math.cos(rad * 1.2) * 3
            points.append((px, py))
        if len(points) > 1:
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=ink_color, width=2)
        # Add readable text beneath slightly blurred or matching for hybrid OCR realism
        draw.text((curr_x, start_y - 12), word, fill=ink_color)
        curr_x += w_len + word_spacing

def generate_all_handwritten():
    print("=" * 90)
    print("GENERATING 25 DIVERSE HANDWRITTEN BENCHMARK DOCUMENTS")
    print("=" * 90)

    ground_truth = {}

    for idx, item in enumerate(TOPICS, 1):
        file_name = f"doc_handwritten_{idx:02d}.jpg"

        # Paper background texture (white, lined notebook, or soft warm yellow)
        bg_variant = idx % 3
        if bg_variant == 0:
            doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
            has_lines = True
        elif bg_variant == 1:
            doc = Image.new("RGB", (900, 1200), color=(252, 250, 242))
            has_lines = True
        else:
            doc = Image.new("RGB", (900, 1200), color=(250, 250, 250))
            has_lines = False

        draw = ImageDraw.Draw(doc)

        if has_lines:
            draw_ruled_lines(draw, 900, 1200, line_spacing=44, start_y=200, end_y=1120)

        # Ink color variation (Royal Blue, Dark Navy, Black, Faded Blue-Grey)
        ink_variants = [
            (25, 45, 140),   # Royal Blue
            (15, 30, 95),    # Dark Navy
            (35, 35, 40),    # Ink Black
            (50, 65, 110),   # Faded Blue
        ]
        ink = ink_variants[idx % len(ink_variants)]

        # Header metadata (Date & Place handwritten top right)
        draw.text((620, 80), f"Date: 0{idx % 28 + 1}/02/2026", fill=ink)
        draw.text((620, 110), "Apex University, Pune", fill=ink)

        # Salutation
        draw.text((130, 170), "To,", fill=ink)
        draw.text((130, 210), "The Respected Authority / Head of Department,", fill=ink)
        draw.text((130, 250), "Apex Institute of Higher Education, Pune.", fill=ink)

        # Subject Line
        draw.text((130, 310), f"Subject: Handwritten Note -- {item['subject']}", fill=ink)
        draw.line([130, 335, 780, 335], fill=ink, width=1)

        # Body Paragraphs (Simulated natural handwriting text)
        body_start_y = 380
        body_box_y = body_start_y - 20
        body_box_x = 120
        body_box_w = 720

        # Draw handwritten body lines
        sentences = [
            f"Sir/Madam, I am writing this application regarding {item['subject'].lower()}.",
            item['text'],
            "I request your kind approval and necessary endorsement at the earliest.",
            "I have attached all required documentary references and past semester records.",
            "Thanking you in anticipation for your kind consideration."
        ]

        curr_y = body_start_y
        for s in sentences:
            draw_cursive_sentence(draw, s, 130, curr_y, ink, slant=1.05 + (idx % 3) * 0.05)
            curr_y += 75

        body_box_h = curr_y - body_start_y + 30

        # Sign-off & Student Signature block
        sig_y = curr_y + 40
        draw.text((580, sig_y), "Yours sincerely,", fill=ink)
        draw.text((580, sig_y + 40), item["student"], fill=ink)
        draw.text((580, sig_y + 70), f"Roll: {item['roll']}", fill=ink)

        # Add light blur for natural ink bleed realism
        doc = doc.filter(ImageFilter.GaussianBlur(radius=0.45))

        save_path = OUTPUT_DIR / file_name
        doc.save(save_path, quality=94)

        # Ground truth
        ground_truth[file_name] = {
            "query_target": "handwritten text",
            "subject": item["subject"],
            "student": item["student"],
            "category": "HANDWRITTEN",
            "has_text_match": True,
            "has_visual_match": True,
            "visual_target": "Handwritten Text Body",
            "location_desc": "Center",
            "bbox": {"x": body_box_x, "y": body_box_y, "width": body_box_w, "height": body_box_h},
            "normalized_bbox": {
                "x": round(body_box_x / 900, 4),
                "y": round(body_box_y / 1200, 4),
                "width": round(body_box_w / 900, 4),
                "height": round(body_box_h / 1200, 4)
            }
        }
        print(f"  [{idx:02d}/25] Generated {file_name} | Subj: {item['subject']} | Student: {item['student']}")

    # Save Ground Truth JSON
    gt_file = OUTPUT_DIR / "ground_truth_handwritten.json"
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nSuccessfully generated 25 diverse handwritten documents in {OUTPUT_DIR}")
    print(f"Ground truth saved to: {gt_file.name}")
    print("=" * 90)

if __name__ == "__main__":
    generate_all_handwritten()
