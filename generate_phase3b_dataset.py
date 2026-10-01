import io
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import qrcode

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
DATASET_DIR = ROOT_DIR / "dataset" / "phase3b"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 900, 1200

def get_font(size=20, bold=False):
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf" if bold else "calibri.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_header(draw, title, subtitle, banner_color=(30, 58, 138)):
    draw.rectangle([(0, 0), (WIDTH, 70)], fill=banner_color)
    draw.text((WIDTH // 2, 35), title, fill=(255, 255, 255), font=get_font(24, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 95), subtitle, fill=(71, 85, 105), font=get_font(18, bold=True), anchor="mm")
    draw.line([(50, 120), (WIDTH - 50, 120)], fill=(203, 213, 225), width=2)

def draw_footer(draw, note="Apex University Document Portal • Digitally Certified Document"):
    draw.line([(50, HEIGHT - 60), (WIDTH - 50, HEIGHT - 60)], fill=(226, 232, 240), width=1)
    draw.text((WIDTH // 2, HEIGHT - 35), note, fill=(148, 163, 184), font=get_font(12), anchor="mm")

# =============================================================================
# 1. SIGNATURE DOCUMENTS (5 VARIATIONS)
# =============================================================================
def create_signature_docs():
    docs = []
    configs = [
        {
            "id": "doc_sign_01.jpg",
            "title": "FACULTY APPOINTMENT ORDER",
            "sub": "Office of Academic Affairs & Registrar",
            "signatory": "Dr. A. K. Verma, Registrar",
            "loc_desc": "Bottom-Right",
            "coords": (620, 920, 220, 110),
            "ink_color": (15, 23, 140), # Dark Blue
            "banner_color": (30, 58, 138),
            "lines": [
                ("Reference Number: APEX/HR/2026/FAC-8902", True),
                ("Date of Issuance: 12th February 2026", False),
                ("Subject: Formal Appointment and Departmental Clearance", True),
                ("This is to certify that Dr. Rajesh Sharma has completed all statutory clearances", False),
                ("and is confirmed as Associate Professor in Computer Science & Engineering.", False),
                ("Employee Code: EMP-99201. Annual research and doctoral mentorship quota applies.", False),
            ]
        },
        {
            "id": "doc_sign_02.jpg",
            "title": "GRADUATION CLEARANCE CERTIFICATE",
            "sub": "Dean of Student Welfare & Registry",
            "signatory": "Prof. S. R. Deshpande, Dean",
            "loc_desc": "Bottom-Right",
            "coords": (600, 900, 240, 120),
            "ink_color": (20, 30, 160), # Royal Blue
            "banner_color": (15, 118, 110),
            "lines": [
                ("Clearance Serial: CLR/GRAD/2026/4419", True),
                ("Student Name: Amit Vikram Patel (Roll: 2022-CS-114)", False),
                ("Department: Computer Science and Engineering", False),
                ("This certificate confirms that the student has cleared all laboratory dues,", False),
                ("hostel maintenance charges, and central library reference liabilities.", False),
                ("The candidate is eligible for the award of Bachelor of Technology degree.", False),
            ]
        },
        {
            "id": "doc_sign_03.jpg",
            "title": "RESEARCH GRANT APPROVAL MEMORANDUM",
            "sub": "Sponsored Research & Consultancy Directorate",
            "signatory": "Dr. Meenakshi Sundaram, Director",
            "loc_desc": "Bottom-Left",
            "coords": (80, 900, 230, 110),
            "ink_color": (10, 20, 120), # Navy Blue
            "banner_color": (79, 70, 229),
            "lines": [
                ("Project Code: SRIC/AI-VISION/2026/08", True),
                ("Principal Investigator: Dr. K. Ramanathan", False),
                ("Funding Agency: National Science & Technology Board", False),
                ("Sanctioned Budget: INR 45,00,000/- for Cloud Computational Infrastructure.", False),
                ("The procurement of GPU compute cluster is authorized under Tier-1 guidelines.", False),
                ("Progress reports must be submitted bi-annually to the advisory board.", False),
            ]
        },
        {
            "id": "doc_sign_04.jpg",
            "title": "HOSTEL LEAVE & TRAVEL AUTHORIZATION",
            "sub": "Council of Wardens & Campus Residence",
            "signatory": "Chief Warden, Boys Hostel 3",
            "loc_desc": "Bottom-Right",
            "coords": (610, 890, 230, 115),
            "ink_color": (30, 41, 59), # Black Ink
            "banner_color": (180, 83, 9),
            "lines": [
                ("Outstation Gate Pass: HOSTEL/GP/2026/902", True),
                ("Resident Name: Nikhil Joshi (Room B-304)", False),
                ("Period of Leave: 20 Feb 2026 to 25 Feb 2026", False),
                ("Reason: Attending National Academic Conference at IIT Delhi.", False),
                ("Parental consent verified via electronic authorization system.", False),
                ("Resident must report back before 22:00 hrs on the return date.", False),
            ]
        },
        {
            "id": "doc_sign_05.jpg",
            "title": "PROVISIONAL DEGREE ENDORSEMENT",
            "sub": "Office of Controller of Examinations",
            "signatory": "Prof. N. K. Murthy, CoE",
            "loc_desc": "Bottom-Right",
            "coords": (600, 910, 240, 120),
            "ink_color": (15, 23, 140), # Dark Blue
            "banner_color": (67, 56, 202),
            "lines": [
                ("Endorsement Ref: COE/PROV/2026/1029", True),
                ("Candidate: Priya Ananth (Registration: APEX-2022-EE-089)", False),
                ("Program: B.Tech Electrical & Electronics Engineering", False),
                ("Final CGPA: 9.15 (First Class with Distinction)", True),
                ("This provisional degree is issued pending the formal convocation ceremony.", False),
                ("All academic records have been verified against central ledger archives.", False),
            ]
        }
    ]

    for cfg in configs:
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw_header(draw, cfg["title"], cfg["sub"], cfg["banner_color"])

        y = 160
        for text, is_bold in cfg["lines"]:
            draw.text((60, y), text, fill=(15, 23, 42) if is_bold else (51, 65, 85), font=get_font(17 if is_bold else 16, bold=is_bold))
            y += 38

        sx, sy, sw, sh = cfg["coords"]
        draw.text((sx, sy - 22), "Authorized Signature:", fill=(71, 85, 105), font=get_font(14, bold=True))
        # Draw realistic cursive signature strokes
        pts = [
            (sx + 15, sy + 60), (sx + 40, sy + 25), (sx + 65, sy + 70),
            (sx + 95, sy + 20), (sx + 125, sy + 65), (sx + 155, sy + 35),
            (sx + 185, sy + 55), (sx + 215, sy + 40)
        ]
        draw.line(pts, fill=cfg["ink_color"], width=4, joint="curve")
        draw.line([(sx + 10, sy + 75), (sx + sw - 15, sy + 75)], fill=cfg["ink_color"], width=2)
        draw.text((sx + 10, sy + 85), cfg["signatory"], fill=(30, 41, 59), font=get_font(13))

        draw_footer(draw)
        img_path = DATASET_DIR / cfg["id"]
        img.save(img_path, quality=95)
        docs.append({
            "file_name": cfg["id"],
            "target_type": "signature",
            "bbox": {"x": sx, "y": sy, "width": sw, "height": sh},
            "location": cfg["loc_desc"],
            "title": cfg["title"]
        })
    return docs

# =============================================================================
# 2. OFFICIAL STAMP / SEAL DOCUMENTS (5 VARIATIONS)
# =============================================================================
def create_stamp_docs():
    docs = []
    configs = [
        {
            "id": "doc_stamp_01.jpg",
            "title": "TRANSCRIPT VERIFICATION CERTIFICATE",
            "sub": "Controller of Examinations Division",
            "seal_text": ("APEX UNIVERSITY", "OFFICIAL SEAL", "★ VERIFIED ★"),
            "loc_desc": "Bottom-Left",
            "coords": (80, 890, 160, 160),
            "stamp_color": (190, 24, 24), # Red
            "banner_color": (30, 58, 138),
            "lines": [
                ("Verification Code: VERIF/TRANS/2026/8831", True),
                ("Candidate: Ananya Deshmukh (Enrollment: APEX-BT-2022-0441)", False),
                ("Program: Bachelor of Technology in Computer Science", False),
                ("CGPA: 9.42 / 10.00 (First Class with Distinction)", True),
                ("Statement of Attestation: Credits comply with AICTE norms.", False),
                ("The official red seal below validates the authenticity of this record.", False),
            ]
        },
        {
            "id": "doc_stamp_02.jpg",
            "title": "NO DUES ATTESTATION CERTIFICATE",
            "sub": "Finance & Accounts Department",
            "seal_text": ("FINANCE DIVISION", "ACCOUNTS PAID", "✔ AUDITED ✔"),
            "loc_desc": "Bottom-Left",
            "coords": (90, 900, 155, 155),
            "stamp_color": (13, 148, 136), # Teal
            "banner_color": (15, 118, 110),
            "lines": [
                ("Accounts Ref: FIN/NODUES/2026/301", True),
                ("Student: Sandeep Kulkarni (ID: 2022-MECH-502)", False),
                ("Fee Status: All 8 Semesters Tuition & Exam Fees Paid in Full.", True),
                ("Security Deposit Refund: Approved and processed via NEFT.", False),
                ("No outstanding dues remain across any department ledger.", False),
            ]
        },
        {
            "id": "doc_stamp_03.jpg",
            "title": "GOVERNMENT SCHOLARSHIP APPROVAL",
            "sub": "National Welfare & Educational Grants Cell",
            "seal_text": ("SCHOLARSHIP CELL", "STATE GOVT", "★ SANCTIONED ★"),
            "loc_desc": "Bottom-Left",
            "coords": (85, 885, 165, 165),
            "stamp_color": (185, 28, 28), # Deep Red
            "banner_color": (185, 28, 28),
            "lines": [
                ("Grant Sanction ID: GOV/SCH/2026/MAH-9921", True),
                ("Beneficiary: Pooja Patil (Merit-Cum-Means Scheme)", False),
                ("Disbursement Amount: INR 50,000 per Academic Year", True),
                ("Institution: Apex University Faculty of Engineering", False),
                ("Direct Bank Transfer authorized under Welfare Scheme.", False),
            ]
        },
        {
            "id": "doc_stamp_04.jpg",
            "title": "LIBRARY REFERENCE CLEARANCE",
            "sub": "University Central Library Directorate",
            "seal_text": ("CENTRAL LIBRARY", "BOOKS RETURNED", "★ CLEARED ★"),
            "loc_desc": "Bottom-Left",
            "coords": (80, 895, 160, 160),
            "stamp_color": (67, 56, 202), # Indigo
            "banner_color": (79, 70, 229),
            "lines": [
                ("Library Clearance Slip: LIB/CLR/2026/184", True),
                ("Member: Vikram Seth (Card: LIB-2022-CS-99)", False),
                ("Status: Zero books pending return. RFID tag deactivated.", False),
                ("Reading Hall Access: Concluded for current graduation batch.", False),
                ("Official stamp confirms zero outstanding library fines.", False),
            ]
        },
        {
            "id": "doc_stamp_05.jpg",
            "title": "BONAFIDE STUDENT CERTIFICATE",
            "sub": "Registrar Office & Academic Verification",
            "seal_text": ("APEX REGISTRAR", "OFFICIAL RECORD", "★ BONAFIDE ★"),
            "loc_desc": "Bottom-Right",
            "coords": (640, 890, 160, 160),
            "stamp_color": (180, 24, 24), # Crimson
            "banner_color": (30, 58, 138),
            "lines": [
                ("Bonafide Certificate No: APEX/BON/2026/774", True),
                ("To Whom It May Concern:", True),
                ("This is to certify that Rahul Nair is a bonafide student of this university", False),
                ("enrolled in the 4-year B.Tech Information Technology program.", False),
                ("Academic Term: 2022-2026. General conduct has been exemplary.", False),
            ]
        }
    ]

    for cfg in configs:
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw_header(draw, cfg["title"], cfg["sub"], cfg["banner_color"])

        y = 160
        for text, is_bold in cfg["lines"]:
            draw.text((60, y), text, fill=(15, 23, 42) if is_bold else (51, 65, 85), font=get_font(17 if is_bold else 16, bold=is_bold))
            y += 38

        sx, sy, sw, sh = cfg["coords"]
        col = cfg["stamp_color"]
        draw.ellipse([(sx, sy), (sx + sw, sy + sh)], outline=col, width=4)
        draw.ellipse([(sx + 10, sy + 10), (sx + sw - 10, sy + sh - 10)], outline=col, width=2)
        l1, l2, l3 = cfg["seal_text"]
        draw.text((sx + sw // 2, sy + 40), l1, fill=col, font=get_font(12, bold=True), anchor="mm")
        draw.text((sx + sw // 2, sy + 80), l2, fill=col, font=get_font(14, bold=True), anchor="mm")
        draw.text((sx + sw // 2, sy + 120), l3, fill=col, font=get_font(12, bold=True), anchor="mm")

        draw_footer(draw)
        img_path = DATASET_DIR / cfg["id"]
        img.save(img_path, quality=95)
        docs.append({
            "file_name": cfg["id"],
            "target_type": "stamp",
            "bbox": {"x": sx, "y": sy, "width": sw, "height": sh},
            "location": cfg["loc_desc"],
            "title": cfg["title"]
        })
    return docs

# =============================================================================
# 3. STUDENT PORTRAIT PHOTOGRAPH DOCUMENTS (5 VARIATIONS)
# =============================================================================
def create_photo_docs():
    docs = []
    configs = [
        {
            "id": "doc_photo_01.jpg",
            "title": "STUDENT SMART IDENTITY CARD",
            "sub": "Central Campus Registry & Student Services",
            "loc_desc": "Top-Right",
            "coords": (670, 150, 160, 200),
            "bg_color": (186, 215, 248), # Blue portrait background
            "blazer_color": (30, 58, 138),
            "banner_color": (30, 58, 138),
            "lines": [
                ("Student Name: Rohan Mukherjee", True),
                ("Roll Number: 2026-CS-0912", True),
                ("Department: Information Technology", False),
                ("Card Validity: July 2026 - June 2030", False),
                ("Campus Privileges: 24/7 Digital Reference Library Wing", False),
                ("Non-transferable smart identity badge.", False),
            ]
        },
        {
            "id": "doc_photo_02.jpg",
            "title": "EXAMINATION ADMIT CARD & PHOTO ID",
            "sub": "National Examination Board Center",
            "loc_desc": "Top-Right",
            "coords": (660, 145, 165, 205),
            "bg_color": (199, 210, 254), # Indigo portrait background
            "blazer_color": (67, 56, 202),
            "banner_color": (67, 56, 202),
            "lines": [
                ("Candidate: Sneha Kulkarni", True),
                ("Hall Ticket ID: 2026-ADMIT-7712", True),
                ("Center: Complex Hall 3, Main Campus", False),
                ("Exam Date: 20th February 2026 (09:00 AM)", False),
                ("Photograph must match candidate face at turnstile.", False),
            ]
        },
        {
            "id": "doc_photo_03.jpg",
            "title": "CAMPUS HOSTEL RESIDENT BADGE",
            "sub": "Hostel Affairs & Student Housing Directorate",
            "loc_desc": "Top-Right",
            "coords": (670, 150, 160, 200),
            "bg_color": (254, 215, 170), # Amber portrait background
            "blazer_color": (180, 83, 9),
            "banner_color": (180, 83, 9),
            "lines": [
                ("Resident: Tanmay Joshi", True),
                ("Hostel Block: Aryabhatta Hall Room 402", False),
                ("Emergency Contact: +91-9876543210", False),
                ("Mess Plan: Platinum Unlimited Dining", False),
                ("Resident photo verified by hostel warden office.", False),
            ]
        },
        {
            "id": "doc_photo_04.jpg",
            "title": "FACULTY RESEARCH FELLOW ID",
            "sub": "Dean of Research & Sponsored Projects",
            "loc_desc": "Top-Right",
            "coords": (665, 150, 160, 200),
            "bg_color": (204, 251, 241), # Teal background
            "blazer_color": (15, 118, 110),
            "banner_color": (15, 118, 110),
            "lines": [
                ("Fellow Name: Dr. Ananya Sen", True),
                ("Designation: Senior Postdoctoral Fellow", True),
                ("Laboratory: High Performance Quantum Computing", False),
                ("Access Tier: Level-4 Cleanroom & Server Cluster", False),
                ("Photo identification required for lab ingress.", False),
            ]
        },
        {
            "id": "doc_photo_05.jpg",
            "title": "SPORTS COUNCIL ATHLETE PASS",
            "sub": "Directorate of Physical Education & Sports",
            "loc_desc": "Top-Right",
            "coords": (670, 150, 160, 200),
            "bg_color": (220, 252, 231), # Green background
            "blazer_color": (22, 101, 52),
            "banner_color": (22, 101, 52),
            "lines": [
                ("Athlete Name: Kabir Mehta", True),
                ("Sport Discipline: Badminton (University Team Captain)", False),
                ("Gymnasium & Olympic Pool Access Pass", False),
                ("National Inter-University Championship 2026", False),
                ("Official athlete photograph identification card.", False),
            ]
        }
    ]

    for cfg in configs:
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw_header(draw, cfg["title"], cfg["sub"], cfg["banner_color"])

        y = 160
        for text, is_bold in cfg["lines"]:
            draw.text((60, y), text, fill=(15, 23, 42) if is_bold else (51, 65, 85), font=get_font(17 if is_bold else 16, bold=is_bold))
            y += 38

        px, py, pw, ph = cfg["coords"]
        draw.rectangle([(px - 4, py - 4), (px + pw + 4, py + ph + 4)], fill=(226, 232, 240), outline=(148, 163, 184), width=1)
        draw.rectangle([(px, py), (px + pw, py + ph)], fill=cfg["bg_color"])
        # Silhouette Portrait
        hcx, hcy = px + pw // 2, py + 70
        draw.ellipse([(hcx - 35, hcy - 45), (hcx + 35, hcy + 35)], fill=(225, 185, 155)) # Face
        draw.ellipse([(hcx - 37, hcy - 48), (hcx + 37, hcy - 10)], fill=(30, 41, 59)) # Hair
        draw.ellipse([(px + 15, py + 110), (px + pw - 15, py + ph + 30)], fill=cfg["blazer_color"]) # Blazer

        draw_footer(draw)
        img_path = DATASET_DIR / cfg["id"]
        img.save(img_path, quality=95)
        docs.append({
            "file_name": cfg["id"],
            "target_type": "photo",
            "bbox": {"x": px, "y": py, "width": pw, "height": ph},
            "location": cfg["loc_desc"],
            "title": cfg["title"]
        })
    return docs

# =============================================================================
# 4. QR CODE DOCUMENTS (5 VARIATIONS)
# =============================================================================
def create_qr_docs():
    docs = []
    configs = [
        {
            "id": "doc_qr_01.jpg",
            "title": "EXAMINATION HALL TICKET",
            "sub": "National Assessment Directorate",
            "loc_desc": "Bottom-Right",
            "coords": (680, 920, 150, 150),
            "banner_color": (30, 58, 138),
            "payload": "https://apex.edu.in/exam/verify/7719",
            "lines": [
                ("Candidate: Sneha Kulkarni (Hall Ticket: 2026-HT-7719)", True),
                ("Exam: Distributed Cloud Architecture CS-401", False),
                ("Reporting Time: 08:30 AM Sharp at Complex Hall B", False),
                ("Scan QR code below at entrance turnstile.", False),
            ]
        },
        {
            "id": "doc_qr_02.jpg",
            "title": "TUITION FEE RECEIPT & E-VOUCHER",
            "sub": "Finance & Accounts Department",
            "loc_desc": "Bottom-Right",
            "coords": (680, 915, 150, 150),
            "banner_color": (15, 118, 110),
            "payload": "https://apex.edu.in/fees/receipt/FEE-9042",
            "lines": [
                ("Transaction Ref: TXN-2026-FEE-9042", True),
                ("Payer: Siddharth Rao (Enrollment: APEX-2022-09)", False),
                ("Total Amount Paid: INR 85,000/- (Semester VIII Tuition)", True),
                ("Payment Mode: Unified Payments Interface (UPI)", False),
                ("Scan QR code to verify bank transaction authenticity.", False),
            ]
        },
        {
            "id": "doc_qr_03.jpg",
            "title": "NATIONAL CONVOCATION DEGREE",
            "sub": "Office of Vice Chancellor & Senate",
            "loc_desc": "Bottom-Left",
            "coords": (80, 920, 150, 150),
            "banner_color": (79, 70, 229),
            "payload": "https://apex.edu.in/convocation/degree/BE-4412",
            "lines": [
                ("Degree Awarded: Bachelor of Engineering (Honors)", True),
                ("Graduate: Aakash Sharma (CGPA: 9.60)", False),
                ("Senate Resolution No: SENATE/CONF/2026/04", False),
                ("Permanent Academic Record ID: APEX-DEG-2026-881", True),
                ("Tamper-proof QR code verifies National Academic Depository record.", False),
            ]
        },
        {
            "id": "doc_qr_04.jpg",
            "title": "RESEARCH CONFERENCE BADGE PASS",
            "sub": "International Conference on Machine Learning",
            "loc_desc": "Bottom-Right",
            "coords": (680, 910, 150, 150),
            "banner_color": (180, 83, 9),
            "payload": "https://icml2026.org/attendee/ICML-DELEGATE-402",
            "lines": [
                ("Delegate Pass: Dr. Suresh Menon", True),
                ("Affiliation: Apex University Department of AI", False),
                ("Access: All Keynote Sessions & Workshops", False),
                ("Conference Venue: Auditorium Complex Hall 1", False),
                ("Scan QR badge for electronic attendance logging.", False),
            ]
        },
        {
            "id": "doc_qr_05.jpg",
            "title": "VEHICLE PARKING PERMIT PASS",
            "sub": "Campus Security & Traffic Management Directorate",
            "loc_desc": "Bottom-Right",
            "coords": (675, 915, 150, 150),
            "banner_color": (30, 41, 59),
            "payload": "https://apex.edu.in/security/parking/PERMIT-099",
            "lines": [
                ("Permit Serial: PARK/FACULTY/2026/099", True),
                ("Vehicle Registration: MH-12-AP-8802", False),
                ("Permitted Parking: Staff Zone P-2 (Academic Block)", False),
                ("Validity: Academic Session 2026-2027", False),
                ("Automated boom barrier scans QR code for gate access.", False),
            ]
        }
    ]

    for cfg in configs:
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw_header(draw, cfg["title"], cfg["sub"], cfg["banner_color"])

        y = 160
        for text, is_bold in cfg["lines"]:
            draw.text((60, y), text, fill=(15, 23, 42) if is_bold else (51, 65, 85), font=get_font(17 if is_bold else 16, bold=is_bold))
            y += 38

        qx, qy, qw, qh = cfg["coords"]
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(cfg["payload"])
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_img = qr_img.resize((qw, qh), Image.Resampling.LANCZOS)
        img.paste(qr_img, (qx, qy))

        draw_footer(draw)
        img_path = DATASET_DIR / cfg["id"]
        img.save(img_path, quality=95)
        docs.append({
            "file_name": cfg["id"],
            "target_type": "qr_code",
            "bbox": {"x": qx, "y": qy, "width": qw, "height": qh},
            "location": cfg["loc_desc"],
            "title": cfg["title"]
        })
    return docs

# =============================================================================
# 5. TEXT-ONLY CONTROL DOCUMENTS (5 VARIATIONS)
# =============================================================================
def create_text_only_docs():
    docs = []
    configs = [
        {
            "id": "doc_text_01.jpg",
            "title": "CAMPUS CLEANLINESS ADVISORY",
            "sub": "Estate Management & Maintenance Directorate",
            "banner_color": (30, 58, 138),
            "lines": [
                ("Circular Ref: CIR/ESTATE/2026/04", True),
                ("Subject: Waste Segregation & Green Campus Initiative", True),
                ("All academic blocks and student residences must follow separate bins.", False),
                ("Single-use plastic bottles are strictly prohibited across campus.", False),
                ("Daily housekeeping schedules run from 06:00 AM to 02:00 PM.", False),
            ]
        },
        {
            "id": "doc_text_02.jpg",
            "title": "SEMESTER EXAMINATION TIMETABLE",
            "sub": "Academic Scheduling & Timetable Committee",
            "banner_color": (15, 118, 110),
            "lines": [
                ("Notification: TIME/EXAM/2026/01", True),
                ("Schedule for B.Tech End-Semester Theory Papers:", True),
                ("• 18 Feb: CS-401 Distributed Computing (09:30 AM)", False),
                ("• 20 Feb: CS-402 Computer Vision & Deep Learning (09:30 AM)", False),
                ("• 23 Feb: CS-403 Network Security Protocols (09:30 AM)", False),
            ]
        },
        {
            "id": "doc_text_03.jpg",
            "title": "HOSTEL CODE OF CONDUCT & RULES",
            "sub": "Council of Wardens & Student Living",
            "banner_color": (180, 83, 9),
            "lines": [
                ("Rulebook Edition: 2026-2027", True),
                ("1. Night curfew is strictly enforced at 22:00 hrs for all residences.", False),
                ("2. Visitors are permitted in the ground floor lounge area only.", False),
                ("3. Heavy electrical appliances are not permitted inside dorm rooms.", False),
                ("4. Quiet hours must be maintained from 23:00 to 06:00 hrs.", False),
            ]
        },
        {
            "id": "doc_text_04.jpg",
            "title": "ANNUAL CULTURAL FESTIVAL NOTICE",
            "sub": "Student Activities & Cultural Council",
            "banner_color": (79, 70, 229),
            "lines": [
                ("Fest Announcement: EUPHORIA 2026", True),
                ("Dates: 14th to 16th March 2026 at Main Campus Amphitheater", False),
                ("Events: Inter-Collegiate Dance, Music, Drama, and Coding Hackathon.", False),
                ("Registration portal opens on 01st March for university delegates.", False),
                ("Volunteers may contact the student council cultural secretary.", False),
            ]
        },
        {
            "id": "doc_text_05.jpg",
            "title": "CENTRAL LIBRARY REFERENCE GUIDELINES",
            "sub": "University Library System & E-Resources",
            "banner_color": (67, 56, 202),
            "lines": [
                ("Library Advisory: LIB/GUIDE/2026/02", True),
                ("1. General book circulation is allowed for up to 14 days per loan.", False),
                ("2. Online IEEE and ACM digital libraries are accessible via campus VPN.", False),
                ("3. Group study discussion cubicles can be booked via the mobile portal.", False),
                ("4. Silence must be observed in the second-floor research reference section.", False),
            ]
        }
    ]

    for cfg in configs:
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw_header(draw, cfg["title"], cfg["sub"], cfg["banner_color"])

        y = 160
        for text, is_bold in cfg["lines"]:
            draw.text((60, y), text, fill=(15, 23, 42) if is_bold else (51, 65, 85), font=get_font(17 if is_bold else 16, bold=is_bold))
            y += 38

        draw_footer(draw)
        img_path = DATASET_DIR / cfg["id"]
        img.save(img_path, quality=95)
        docs.append({
            "file_name": cfg["id"],
            "target_type": "none",
            "bbox": None,
            "location": "None",
            "title": cfg["title"]
        })
    return docs

def generate_full_benchmark():
    print("=" * 85)
    print("GENERATING COMPREHENSIVE 25-DOCUMENT PHASE 3B BENCHMARK DATASET")
    print("=" * 85)

    all_docs = []
    all_docs.extend(create_signature_docs())
    all_docs.extend(create_stamp_docs())
    all_docs.extend(create_photo_docs())
    all_docs.extend(create_qr_docs())
    all_docs.extend(create_text_only_docs())

    gt_path = DATASET_DIR / "ground_truth_phase3b.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, indent=2)

    print(f"Successfully generated {len(all_docs)} benchmark documents in {DATASET_DIR}")
    print(f"  • Signatures: 5 documents (doc_sign_01..05.jpg)")
    print(f"  • Stamps / Seals: 5 documents (doc_stamp_01..05.jpg)")
    print(f"  • Photographs: 5 documents (doc_photo_01..05.jpg)")
    print(f"  • QR Codes: 5 documents (doc_qr_01..05.jpg)")
    print(f"  • Text-Only Controls: 5 documents (doc_text_01..05.jpg)")
    print(f"Ground truth bounding boxes saved to: {gt_path.name}")
    print("=" * 85)

if __name__ == "__main__":
    generate_full_benchmark()
