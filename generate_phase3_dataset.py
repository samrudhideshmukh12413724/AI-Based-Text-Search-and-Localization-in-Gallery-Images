import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode

ROOT_DIR = Path(__file__).resolve().parent
PHASE3_DIR = ROOT_DIR / "dataset" / "phase3"
POS_DIR = PHASE3_DIR / "positive"
NEG_DIR = PHASE3_DIR / "negative"
MULTI_DIR = PHASE3_DIR / "multi_qr"
DIFF_DIR = PHASE3_DIR / "difficult"
GT_FILE = PHASE3_DIR / "ground_truth_phase3.json"

for d in [POS_DIR, NEG_DIR, MULTI_DIR, DIFF_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def get_font(size: int, bold: bool = False):
    try:
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(font_name, size)
    except Exception:
        return ImageFont.load_default()

def make_qr_image(data: str, box_size: int = 4, border: int = 1) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")

def create_document_base(title: str, subtitle: str, lines: list[str], width: int = 900, height: int = 1200) -> Image.Image:
    img = Image.new("RGB", (width, height), color="#FAFAFA")
    draw = ImageDraw.Draw(img)

    # Outer border & header bar
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#CBD5E1", width=2)
    draw.rectangle([(20, 20), (width - 20, 110)], fill="#1E3A8A")

    title_font = get_font(28, bold=True)
    draw.text((40, 45), title, fill="#FFFFFF", font=title_font)

    sub_font = get_font(18, bold=True)
    draw.text((40, 140), subtitle, fill="#1E293B", font=sub_font)

    draw.line([(40, 175), (width - 40, 175)], fill="#E2E8F0", width=2)

    body_font = get_font(16)
    y_text = 200
    for line in lines:
        draw.text((40, y_text), line, fill="#334155", font=body_font)
        y_text += 32

    # Footer
    footer_font = get_font(12)
    draw.line([(40, height - 60), (width - 40, height - 60)], fill="#E2E8F0", width=1)
    draw.text((40, height - 45), "Apex University Document Portal • Digitally Generated", fill="#94A3B8", font=footer_font)

    return img

def build_dataset():
    ground_truth = {}

    print("Generating Phase 3 Dataset...")

    # =========================================================================
    # 1. POSITIVE SAMPLES (10 Single QR Documents)
    # =========================================================================
    pos_specs = [
        (
            "doc_qr_01_scholarship.jpg",
            "GOVERNMENT SCHOLARSHIP PORTAL",
            "Merit-Cum-Means Financial Assistance Grant 2026",
            [
                "Student Name: Rahul Sharma",
                "Enrollment ID: APEX-SCH-2026-0881",
                "Department: Computer Science & Engineering",
                "Grant Amount: Rs. 50,000 / Academic Year",
                "Status: Approved and Verified",
                "",
                "Scan the official QR code below to verify grant authenticity",
                "and electronic disbursement authorization.",
            ],
            "https://apex.edu.in/verify/scholarship/0881",
            (680, 960, 160, 160),
            "Bottom-Right",
        ),
        (
            "doc_qr_02_admit_card.jpg",
            "EXAMINATION ADMIT CARD",
            "End-Semester Examination Date Sheet & Hall Ticket",
            [
                "Candidate: Priya Patel",
                "Roll Number: 2026-EXAM-4412",
                "Exam Center: Main Campus Auditorium Hall 3",
                "Reporting Time: 09:00 AM Sharp",
                "Instructions: Candidate must present this digital pass",
                "with the security QR code at the exam gate.",
            ],
            "https://apex.edu.in/exam/verify/hallticket/4412",
            (700, 130, 150, 150),
            "Top-Right",
        ),
        (
            "doc_qr_03_fee_receipt.jpg",
            "COLLEGE FEE PAYMENT RECEIPT",
            "Tuition & Laboratory Fee Challan Receipt",
            [
                "Payer Name: Vikram Singh",
                "Challan Number: CH-2026-9011",
                "Total Amount Paid: Rs. 75,000",
                "Payment Mode: Online Net Banking",
                "Transaction Status: SUCCESS",
                "",
                "Bank reference QR code for accounts verification:",
            ],
            "https://apex.edu.in/finance/receipt/9011",
            (50, 960, 150, 150),
            "Bottom-Left",
        ),
        (
            "doc_qr_04_bonafide.jpg",
            "BONAFIDE STUDENT CERTIFICATE",
            "Official Institutional Verification Certificate",
            [
                "This is to certify that Sneha Deshmukh is a bona fide student",
                "of Bachelor of Technology (Information Technology) in semester 6.",
                "This certificate is issued for educational loan processing.",
                "Authorized Signatory: Office of the Dean Academics.",
            ],
            "https://apex.edu.in/cert/bonafide/2026-IT-55",
            (370, 920, 160, 160),
            "Bottom-Center",
        ),
        (
            "doc_qr_05_hostel_pass.jpg",
            "HOSTEL RESIDENCE GATE PASS",
            "Hostel Night-Out & Extended Leave Pass",
            [
                "Resident: Amit Kumar (Hostel Block B, Room 304)",
                "Leave Duration: 25-Aug-2026 to 28-Aug-2026",
                "Reason: Family Academic Visit",
                "Warden Approval: Verified & Cleared",
            ],
            "https://apex.edu.in/hostel/pass/H-9921",
            (700, 140, 140, 140),
            "Top-Right",
        ),
        (
            "doc_qr_06_placement_shortlist.jpg",
            "CAMPUS PLACEMENT SHORTLIST",
            "Google Summer Technical Internship Shortlist",
            [
                "Company: Google India Engineering",
                "Selected Candidate: Ananya Verma",
                "Role: Software Development Intern",
                "Stipend: Rs. 1,10,000 / month",
                "Scan to confirm interview slot & portal onboarding.",
            ],
            "https://apex.edu.in/placement/shortlist/google/401",
            (680, 960, 150, 150),
            "Bottom-Right",
        ),
        (
            "doc_qr_07_library_card.jpg",
            "CENTRAL LIBRARY DIGITAL PASS",
            "IEEE Journal Access & Book Borrowing Card",
            [
                "Member: Rohan Joshi",
                "Card ID: LIB-MEM-8832",
                "Allowed Checkouts: 5 Books / 30 Days",
                "Digital Database: IEEE Xplore & Springer Link Access Active",
            ],
            "https://apex.edu.in/library/member/8832",
            (680, 500, 150, 150),
            "Center-Right",
        ),
        (
            "doc_qr_08_sports_trial.jpg",
            "INTER-COLLEGE SPORTS BADMINTON PASS",
            "State Level Championship Trial Registration",
            [
                "Athlete Name: Karan Mehra",
                "Event: Men's Singles Badminton Tournament",
                "Chest Number: #82",
                "Venue: Indoor Sports Complex, Court 1",
            ],
            "https://apex.edu.in/sports/badge/82",
            (680, 960, 150, 150),
            "Bottom-Right",
        ),
        (
            "doc_qr_09_workshop_cert.jpg",
            "AI & MACHINE LEARNING BOOTCAMP",
            "Hands-on Workshop Completion Certificate",
            [
                "Participant: Divya Nair",
                "Topic: Deep Learning & Computer Vision with PyTorch",
                "Duration: 40 Hours Intensive Lab Sessions",
                "Digital Credential Verification ID: AI-2026-092",
            ],
            "https://apex.edu.in/verify/workshop/ai-092",
            (370, 930, 160, 160),
            "Bottom-Center",
        ),
        (
            "doc_qr_10_counseling_letter.jpg",
            "CENTRALIZED ADMISSION COUNSELING",
            "Seat Allotment & Document Verification Schedule",
            [
                "Candidate Rank: AIR 1420",
                "Allotted Branch: B.Tech Artificial Intelligence & Data Science",
                "Reporting Center: Admissions Block, Room 102",
                "Scan for live counseling queue tracking.",
            ],
            "https://apex.edu.in/admission/counseling/1420",
            (700, 140, 140, 140),
            "Top-Right",
        ),
    ]

    for filename, title, subtitle, lines, qr_data, bbox, loc_desc in pos_specs:
        img = create_document_base(title, subtitle, lines)
        gx, gy, gw, gh = bbox
        qr_img = make_qr_image(qr_data)
        qr_resized = qr_img.resize((gw, gh), Image.Resampling.LANCZOS)
        img.paste(qr_resized, (gx, gy))

        filepath = POS_DIR / filename
        img.save(filepath, quality=95)

        ground_truth[filename] = {
            "relative_path": f"positive/{filename}",
            "contains_qr": True,
            "count": 1,
            "objects": [
                {
                    "type": "qr_code",
                    "bbox": {"x": gx, "y": gy, "width": gw, "height": gh},
                    "data": qr_data,
                    "location_desc": loc_desc,
                }
            ],
        }
        print(f"  [+] Created Positive: {filename} with QR at {bbox}")

    # =========================================================================
    # 2. NEGATIVE SAMPLES (5 No-QR Documents)
    # =========================================================================
    neg_specs = [
        (
            "doc_neg_01_cleanliness_notice.jpg",
            "CAMPUS CLEANLINESS DRIVE",
            "Green Campus & Sustainability Initiative 2026",
            [
                "All students and faculty members are invited to participate in the",
                "annual Swachh Campus cleanliness drive on Saturday at 8:00 AM.",
                "Volunteers will receive activity certificates and community hours.",
                "Meeting point: Central Lawn fountain area.",
            ],
        ),
        (
            "doc_neg_02_holiday_calendar.jpg",
            "ACADEMIC HOLIDAY LIST 2026",
            "Semester 1 & 2 Gazetted Holidays",
            [
                "• Republic Day: 26 January",
                "• Holi Festival: 25 March",
                "• Independence Day: 15 August",
                "• Diwali Break: 31 October - 03 November",
                "• Winter Vacation: 24 December - 02 January",
            ],
        ),
        (
            "doc_neg_03_timetable.jpg",
            "WEEKLY CLASS TIMETABLE",
            "B.Tech Computer Science - Section A",
            [
                "Monday: Operating Systems (09:00), Database Management (11:00)",
                "Tuesday: Computer Networks (10:00), AI Lab (14:00 - 17:00)",
                "Wednesday: Theory of Computation (09:00), Software Eng (11:00)",
                "Thursday: Machine Learning (10:00), Web Dev Lab (14:00 - 17:00)",
                "Friday: Cloud Computing (09:00), Technical Seminar (14:00)",
            ],
        ),
        (
            "doc_neg_04_gym_rules.jpg",
            "CAMPUS GYMNASIUM GUIDELINES",
            "Fitness Center Timings & Safety Regulations",
            [
                "1. Morning Slot: 06:00 AM - 09:00 AM (Students & Faculty)",
                "2. Evening Slot: 05:00 PM - 09:00 PM (Hostel Residents)",
                "3. Clean sports shoes and proper gym attire are strictly mandatory.",
                "4. Please re-rack all dumbbells and wipe down equipment after use.",
            ],
        ),
        (
            "doc_neg_05_bus_transport.jpg",
            "CAMPUS BUS TRANSPORT NOTICE",
            "Route Schedule & Annual Transport Pass Fees",
            [
                "Route 1: City Center -> Campus Main Gate (07:30 AM)",
                "Route 2: Metro Station -> Campus Library (07:45 AM)",
                "Annual transport pass fee: Rs. 18,000 / Academic Year.",
                "Pass renewals must be submitted to the transport desk by 15-Sept.",
            ],
        ),
    ]

    for filename, title, subtitle, lines in neg_specs:
        img = create_document_base(title, subtitle, lines)
        filepath = NEG_DIR / filename
        img.save(filepath, quality=95)

        ground_truth[filename] = {
            "relative_path": f"negative/{filename}",
            "contains_qr": False,
            "count": 0,
            "objects": [],
        }
        print(f"  [-] Created Negative: {filename} (0 QR codes)")

    # =========================================================================
    # 3. MULTI-QR SAMPLES (3 Documents with 2+ QR codes)
    # =========================================================================
    multi_specs = [
        (
            "doc_multi_01_dual_verification.jpg",
            "DEGREE CONVOCATION CERTIFICATE",
            "Bachelor of Engineering Digital Certificate",
            [
                "Graduate: Siddharth Rao",
                "Degree: Bachelor of Engineering in Electronics",
                "Grade: First Class with Distinction",
                "",
                "QR Code 1 (Left): University Registrar Digital Signature",
                "QR Code 2 (Right): Ministry of Education National Academic Depository",
            ],
            [
                ("https://apex.edu.in/verify/registrar/deg-902", (60, 950, 150, 150), "Bottom-Left"),
                ("https://nad.gov.in/verify/student/sid-8812", (680, 950, 150, 150), "Bottom-Right"),
            ],
        ),
        (
            "doc_multi_02_exam_fee_challan.jpg",
            "EXAMINATION FEE DUAL CHALLAN",
            "Student Copy & Bank Accounts Copy",
            [
                "Candidate: Neha Kulkarni",
                "Semester: 6th Semester Regular Examination",
                "Exam Fee: Rs. 3,500",
                "",
                "Left Section: Bank Deposit Verification QR",
                "Right Section: Student Hall Ticket Confirmation QR",
            ],
            [
                ("https://bank.edu/challan/pay/B-4410", (70, 940, 140, 140), "Bottom-Left"),
                ("https://apex.edu.in/exam/challan/verify/S-4410", (690, 940, 140, 140), "Bottom-Right"),
            ],
        ),
        (
            "doc_multi_03_conference_badge.jpg",
            "ANNUAL TECH SUMMIT DELEGATE BADGE",
            "All-Access Conference & Workshop Pass",
            [
                "Delegate: Dr. Arvind Swaminathan",
                "Affiliation: Department of Computer Science",
                "Access: Keynote Hall + Track A Workshops + Banquet Dinner",
            ],
            [
                ("https://summit.org/badge/keynote/771", (50, 950, 130, 130), "Bottom-Left"),
                ("https://summit.org/badge/workshop/771", (385, 950, 130, 130), "Bottom-Center"),
                ("https://summit.org/badge/banquet/771", (710, 950, 130, 130), "Bottom-Right"),
            ],
        ),
    ]

    for filename, title, subtitle, lines, qrs in multi_specs:
        img = create_document_base(title, subtitle, lines)
        objs = []
        for qr_data, bbox, loc_desc in qrs:
            gx, gy, gw, gh = bbox
            qr_img = make_qr_image(qr_data)
            qr_resized = qr_img.resize((gw, gh), Image.Resampling.LANCZOS)
            img.paste(qr_resized, (gx, gy))
            objs.append({
                "type": "qr_code",
                "bbox": {"x": gx, "y": gy, "width": gw, "height": gh},
                "data": qr_data,
                "location_desc": loc_desc,
            })

        filepath = MULTI_DIR / filename
        img.save(filepath, quality=95)

        ground_truth[filename] = {
            "relative_path": f"multi_qr/{filename}",
            "contains_qr": True,
            "count": len(objs),
            "objects": objs,
        }
        print(f"  [M] Created Multi-QR: {filename} with {len(objs)} QR codes")

    # =========================================================================
    # 4. DIFFICULT SAMPLES (2 Edge Cases)
    # =========================================================================
    diff_specs = [
        (
            "doc_diff_01_small_qr.jpg",
            "CAMPUS ID SMART BADGE",
            "Compact Student Identity Pass",
            [
                "Student ID: APEX-STU-994",
                "Name: Meera Nambiar",
                "Valid Till: June 2028",
                "Small embedded verification barcode at bottom corner:",
            ],
            "https://apex.edu.in/id/verify/994",
            (760, 1050, 75, 75),  # Small 75x75 QR
            "Bottom-Right (Compact)",
        ),
        (
            "doc_diff_02_low_contrast_qr.jpg",
            "GOVERNMENT RESEARCH GRANT NOTICE",
            "Special Scientific Research Allowance",
            [
                "Principal Investigator: Dr. S. Raman",
                "Grant No: DST-SERB-2026-11",
                "Watermarked low-contrast QR verification:",
            ],
            "https://serb.gov.in/grant/DST-11",
            (680, 960, 150, 150),
            "Bottom-Right (Shaded)",
        ),
    ]

    for filename, title, subtitle, lines, qr_data, bbox, loc_desc in diff_specs:
        img = create_document_base(title, subtitle, lines)
        gx, gy, gw, gh = bbox
        qr_img = make_qr_image(qr_data)
        qr_resized = qr_img.resize((gw, gh), Image.Resampling.LANCZOS)
        
        # If low-contrast, apply subtle tint
        if "low_contrast" in filename:
            qr_resized = Image.blend(qr_resized, Image.new("RGB", (gw, gh), "#CBD5E1"), alpha=0.15)

        img.paste(qr_resized, (gx, gy))

        filepath = DIFF_DIR / filename
        img.save(filepath, quality=95)

        ground_truth[filename] = {
            "relative_path": f"difficult/{filename}",
            "contains_qr": True,
            "count": 1,
            "objects": [
                {
                    "type": "qr_code",
                    "bbox": {"x": gx, "y": gy, "width": gw, "height": gh},
                    "data": qr_data,
                    "location_desc": loc_desc,
                }
            ],
        }
        print(f"  [D] Created Difficult: {filename} with QR at {bbox}")

    # Save Ground Truth JSON
    with open(GT_FILE, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\nPhase 3 Dataset Generation Complete! Total images: {len(ground_truth)}")
    print(f"Ground truth saved to: {GT_FILE}")

if __name__ == "__main__":
    build_dataset()
