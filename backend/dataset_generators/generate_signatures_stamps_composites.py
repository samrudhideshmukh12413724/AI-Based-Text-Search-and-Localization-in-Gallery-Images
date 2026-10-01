"""Generates expanded diverse benchmark datasets:
1. 20 Signature Documents (multi-signatory chains, varied inks, positions, flourishes)
2. 20 Official Stamp/Seal Documents (circular, rectangular, purple/red/blue, angled, overlapping)
3. 30 Mixed Composite Documents (Form + Photo + Signature, Form + ID + Stamp, etc.)
4. 15 Structured Hard Negative Documents (Text mentions "signature/stamp/id" but object is physically absent)
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
DATASET_BASE = ROOT_DIR.parent / "dataset"

DIR_SIGNS = DATASET_BASE / "signatures_expanded"
DIR_STAMPS = DATASET_BASE / "stamps_expanded"
DIR_COMPOSITES = DATASET_BASE / "composites_expanded"
DIR_NEGATIVES = DATASET_BASE / "negatives_expanded"

for d in [DIR_SIGNS, DIR_STAMPS, DIR_COMPOSITES, DIR_NEGATIVES]:
    d.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Drawing Helpers
# -----------------------------------------------------------------------------
def draw_signature(draw, start_x, start_y, width, height, stroke_color=(20, 50, 160), style="standard"):
    points = []
    cx = start_x + 15
    cy = start_y + height // 2 + 5
    multiplier = 1.0 if style != "flourish" else 1.5
    for t in range(0, int(width * 0.8), 2):
        rad = math.radians(t * 3.6)
        px = cx + t
        py = cy + math.sin(rad * 2.5) * (14 * multiplier) + math.cos(rad * 1.2) * 8
        points.append((px, py))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=stroke_color, width=3 if style != "fine" else 2)
    # Underline swirl
    draw.arc([start_x + 10, start_y + height - 25, start_x + width - 15, start_y + height - 5], start=160, end=350, fill=stroke_color, width=2)

def draw_official_stamp(draw, cx, cy, radius, ink_color=(180, 20, 20), shape="circle", text="VERIFIED"):
    if shape == "circle":
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=ink_color, width=3)
        draw.ellipse([cx - radius + 10, cy - radius + 10, cx + radius - 10, cy + radius - 10], outline=ink_color, width=1)
        draw.text((cx - 38, cy - 10), text, fill=ink_color)
        draw.text((cx - 50, cy + 12), "APEX UNIVERSITY", fill=ink_color)
    elif shape == "rectangle":
        w = radius * 2 + 20
        h = radius + 15
        draw.rectangle([cx - w//2, cy - h//2, cx + w//2, cy + h//2], outline=ink_color, width=3)
        draw.rectangle([cx - w//2 + 5, cy - h//2 + 5, cx + w//2 - 5, cy + h//2 - 5], outline=ink_color, width=1)
        draw.text((cx - 40, cy - 12), text, fill=ink_color)
        draw.text((cx - 45, cy + 8), "OFFICIAL SEAL", fill=ink_color)
    else:  # oval
        rx = radius + 25
        ry = radius - 10
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=ink_color, width=3)
        draw.text((cx - 45, cy - 8), text, fill=ink_color)

def draw_photo_box(draw, px, py, pw, ph, label="Photo"):
    draw.rectangle([px, py, px + pw, py + ph], fill=(235, 240, 248), outline=(80, 100, 130), width=2)
    cx = px + pw // 2
    cy = py + ph // 2 - 8
    draw.ellipse([cx - 24, cy - 28, cx + 24, cy + 28], fill=(245, 205, 185), outline=(150, 110, 90), width=2)
    draw.ellipse([cx - 36, cy + 32, cx + 36, py + ph + 20], fill=(25, 80, 150))
    draw.text((px + 15, py + ph - 20), f"[{label}]", fill=(70, 70, 70))

def draw_qr_graphic(draw, qx, qy, qw, qh):
    draw.rectangle([qx, qy, qx + qw, qy + qh], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    # 3 Position markers (Top-Left, Top-Right, Bottom-Left)
    cs = qw // 4
    for mx, my in [(qx + 6, qy + 6), (qx + qw - cs - 6, qy + 6), (qx + 6, qy + qh - cs - 6)]:
        draw.rectangle([mx, my, mx + cs, my + cs], fill=(0, 0, 0))
        draw.rectangle([mx + 3, my + 3, mx + cs - 3, my + cs - 3], fill=(255, 255, 255))
        draw.rectangle([mx + 6, my + 6, mx + cs - 6, my + cs - 6], fill=(0, 0, 0))
    # Simulated internal data matrix dots
    for r in range(qy + cs + 10, qy + qh - cs - 5, 8):
        for c in range(qx + 10, qx + qw - 10, 8):
            if random.random() > 0.45:
                draw.rectangle([c, r, c + 5, r + 5], fill=(0, 0, 0))


# -----------------------------------------------------------------------------
# 1. Generate 20 Signature Documents
# -----------------------------------------------------------------------------
def generate_signatures():
    print("\n--- Generating 20 Expanded Signature Documents ---")
    gt = {}
    inks = [(20, 50, 160), (10, 30, 90), (30, 30, 35), (40, 70, 130)]
    roles = ["Dean of Academic Affairs", "Controller of Examinations", "Department Head", "Faculty Advisor", "Chief Proctor"]

    for idx in range(1, 21):
        fname = f"doc_exp_sign_{idx:02d}.jpg"
        doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
        draw = ImageDraw.Draw(doc)
        draw.rectangle([25, 25, 875, 1175], outline=(180, 190, 205), width=2)

        draw.text((160, 50), "APEX UNIVERSITY ACADEMIC ENDORSEMENT", fill=(15, 30, 80))
        draw.line([50, 95, 850, 95], fill=(20, 45, 95), width=2)
        draw.text((180, 135), f"OFFICIAL ENDORSEMENT ORDER #{random.randint(1000, 9999)}", fill=(170, 20, 20))

        # Body paragraphs
        lines = [
            f"This is an official institutional document confirming academic compliance.",
            f"Reference code: APEX-SIGN-2026-{idx:03d} | Student dossier clearance.",
            f"All academic credits and course prerequisites have been rigorously evaluated.",
            f"Approved for graduation degree conferment and academic transcript issuance."
        ]
        y_pos = 200
        for l in lines:
            draw.text((60, y_pos), l, fill=(30, 30, 30))
            y_pos += 45

        # Signature position variations:
        # 1-7: Bottom-Right (standard)
        # 8-14: Bottom-Left
        # 15-20: Dual Signatures (Dean + Registrar)
        ink = inks[idx % len(inks)]
        style = "flourish" if idx % 3 == 0 else "fine" if idx % 3 == 1 else "standard"

        if idx <= 7:
            bx, by, bw, bh = 580, 930, 260, 120
            loc = "Bottom-Right"
            draw.text((bx + 20, by - 20), f"Signed by {roles[idx % len(roles)]}:", fill=(60, 60, 60))
            draw_signature(draw, bx, by, bw, bh, stroke_color=ink, style=style)
            sig_list = [{"bbox": {"x": bx, "y": by, "width": bw, "height": bh}, "loc": loc}]
        elif idx <= 14:
            bx, by, bw, bh = 80, 930, 260, 120
            loc = "Bottom-Left"
            draw.text((bx + 20, by - 20), f"Signed by {roles[idx % len(roles)]}:", fill=(60, 60, 60))
            draw_signature(draw, bx, by, bw, bh, stroke_color=ink, style=style)
            sig_list = [{"bbox": {"x": bx, "y": by, "width": bw, "height": bh}, "loc": loc}]
        else:
            # Dual Signatures
            bx1, by1, bw1, bh1 = 80, 930, 250, 120
            bx2, by2, bw2, bh2 = 580, 930, 250, 120
            loc = "Dual-Bottom"
            draw.text((bx1 + 20, by1 - 20), "Student Signature:", fill=(60, 60, 60))
            draw_signature(draw, bx1, by1, bw1, bh1, stroke_color=(20, 50, 160), style="standard")
            draw.text((bx2 + 20, by2 - 20), "Registrar Signature:", fill=(60, 60, 60))
            draw_signature(draw, bx2, by2, bw2, bh2, stroke_color=(10, 30, 90), style="flourish")
            sig_list = [
                {"bbox": {"x": bx1, "y": by1, "width": bw1, "height": bh1}, "loc": "Bottom-Left"},
                {"bbox": {"x": bx2, "y": by2, "width": bw2, "height": bh2}, "loc": "Bottom-Right"},
            ]

        save_p = DIR_SIGNS / fname
        doc.save(save_p, quality=94)
        gt[fname] = {
            "query_target": "signature",
            "category": "SIGNATURE",
            "has_visual_match": True,
            "visual_target": "Signature",
            "location_desc": loc,
            "signatures": sig_list,
            "bbox": sig_list[0]["bbox"]
        }
        print(f"  [Sign {idx:02d}/20] {fname} | Loc: {loc} | Style: {style}")

    with open(DIR_SIGNS / "ground_truth_signatures.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


# -----------------------------------------------------------------------------
# 2. Generate 20 Stamp Documents
# -----------------------------------------------------------------------------
def generate_stamps():
    print("\n--- Generating 20 Expanded Official Stamp/Seal Documents ---")
    gt = {}
    stamp_colors = [
        (180, 20, 20),   # Official Red
        (110, 30, 140),  # Royal Purple
        (20, 45, 140),   # Deep Blue
        (160, 40, 40),   # Brick Red
    ]
    shapes = ["circle", "rectangle", "oval"]
    texts = ["VERIFIED", "APPROVED", "ADMITTED", "CONFIRMED", "SEALED"]

    for idx in range(1, 21):
        fname = f"doc_exp_stamp_{idx:02d}.jpg"
        doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
        draw = ImageDraw.Draw(doc)
        draw.rectangle([25, 25, 875, 1175], outline=(180, 190, 205), width=2)

        draw.text((150, 50), "APEX UNIVERSITY VERIFICATION DISPATCH", fill=(15, 30, 80))
        draw.line([50, 95, 850, 95], fill=(20, 45, 95), width=2)
        draw.text((170, 135), f"OFFICIAL CERTIFICATION DISPATCH #{random.randint(1000, 9999)}", fill=(170, 20, 20))

        y_pos = 200
        for l in [
            "This official document carries the seal of the institutional registrar.",
            "Any tampering, erasure, or unauthorized alteration invalidates this record.",
            "Valid across all university faculties, examinations, and state authorities.",
            "Signed and stamped in the presence of the executive academic council."
        ]:
            draw.text((60, y_pos), l, fill=(30, 30, 30))
            y_pos += 45

        # Stamp variation
        color = stamp_colors[idx % len(stamp_colors)]
        shape = shapes[idx % len(shapes)]
        txt = texts[idx % len(texts)]

        # Positions: Bottom-Left, Center, Top-Right, Bottom-Right
        pos_id = idx % 4
        if pos_id == 0:
            cx, cy = 200, 940
            loc = "Bottom-Left"
        elif pos_id == 1:
            cx, cy = 450, 850
            loc = "Bottom-Center"
        elif pos_id == 2:
            cx, cy = 720, 260
            loc = "Top-Right"
        else:
            cx, cy = 700, 940
            loc = "Bottom-Right"

        rad = 65
        draw_official_stamp(draw, cx, cy, rad, ink_color=color, shape=shape, text=txt)

        save_p = DIR_STAMPS / fname
        doc.save(save_p, quality=94)
        gt[fname] = {
            "query_target": "official stamp",
            "category": "STAMP",
            "has_visual_match": True,
            "visual_target": f"Official Stamp ({shape.capitalize()})",
            "location_desc": loc,
            "bbox": {"x": cx - rad, "y": cy - rad, "width": rad * 2, "height": rad * 2}
        }
        print(f"  [Stamp {idx:02d}/20] {fname} | Loc: {loc} | Shape: {shape} | Color: {color}")

    with open(DIR_STAMPS / "ground_truth_stamps.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


# -----------------------------------------------------------------------------
# 3. Generate 30 Multi-Object Mixed Composite Documents
# -----------------------------------------------------------------------------
def generate_composites():
    print("\n--- Generating 30 Expanded Multi-Object Mixed Composite Documents ---")
    gt = {}

    for idx in range(1, 31):
        fname = f"doc_exp_composite_{idx:02d}.jpg"
        doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
        draw = ImageDraw.Draw(doc)
        draw.rectangle([25, 25, 875, 1175], outline=(180, 190, 205), width=2)

        # Varying composite combinations:
        # Combo A (idx 1-10): Form + Student Photo + Official Stamp + Signature
        # Combo B (idx 11-20): Hall Ticket + Photo + QR Code + Signature
        # Combo C (idx 21-30): Scholarship Application + Mock ID Card + Stamp + Signature
        combo_type = "Photo_Stamp_Sig" if idx <= 10 else "HallTicket_Photo_QR_Sig" if idx <= 20 else "Scholarship_Card_Stamp_Sig"

        draw.text((150, 50), f"APEX UNIVERSITY -- COMPOSITE DOSSIER #{idx:02d}", fill=(15, 30, 80))
        draw.line([50, 95, 850, 95], fill=(20, 45, 95), width=2)
        draw.text((160, 130), f"MULTI-MODAL VERIFIED DOSSIER: {combo_type}", fill=(180, 20, 20))

        objects_meta = []

        if combo_type == "Photo_Stamp_Sig":
            draw.text((60, 180), "Student Profile Registration: Priya V. Patel | Dept: Computer Science", fill=(10, 10, 10))
            draw.text((60, 215), "Official student identity verified by department registrar with seal.", fill=(50, 50, 50))
            # 1. Photo at Top-Right
            px, py, pw, ph = 690, 170, 140, 170
            draw_photo_box(draw, px, py, pw, ph, label="Student Photo")
            objects_meta.append({"type": "photo", "bbox": {"x": px, "y": py, "width": pw, "height": ph}, "loc": "Top-Right"})

            # 2. Stamp at Bottom-Left
            cx, cy, rad = 200, 950, 65
            draw_official_stamp(draw, cx, cy, rad, ink_color=(180, 20, 20), text="VERIFIED")
            objects_meta.append({"type": "stamp", "bbox": {"x": cx - rad, "y": cy - rad, "width": rad * 2, "height": rad * 2}, "loc": "Bottom-Left"})

            # 3. Signature at Bottom-Right
            sx, sy, sw, sh = 580, 930, 250, 120
            draw.text((sx, sy - 20), "Registrar Signature:", fill=(60, 60, 60))
            draw_signature(draw, sx, sy, sw, sh, stroke_color=(20, 50, 160))
            objects_meta.append({"type": "signature", "bbox": {"x": sx, "y": sy, "width": sw, "height": sh}, "loc": "Bottom-Right"})

        elif combo_type == "HallTicket_Photo_QR_Sig":
            draw.text((60, 180), "Examination Hall Ticket: B.Tech Semester Final Examination", fill=(10, 10, 10))
            draw.text((60, 215), "QR verification required at examination center gate entrance.", fill=(50, 50, 50))
            # 1. Photo at Top-Right
            px, py, pw, ph = 690, 170, 140, 170
            draw_photo_box(draw, px, py, pw, ph, label="Candidate")
            objects_meta.append({"type": "photo", "bbox": {"x": px, "y": py, "width": pw, "height": ph}, "loc": "Top-Right"})

            # 2. QR Code at Bottom-Left
            qx, qy, qw, qh = 80, 900, 150, 150
            draw_qr_graphic(draw, qx, qy, qw, qh)
            objects_meta.append({"type": "qr_code", "bbox": {"x": qx, "y": qy, "width": qw, "height": qh}, "loc": "Bottom-Left"})

            # 3. Signature at Bottom-Right
            sx, sy, sw, sh = 580, 930, 250, 120
            draw.text((sx, sy - 20), "Invigilator Signature:", fill=(60, 60, 60))
            draw_signature(draw, sx, sy, sw, sh, stroke_color=(10, 30, 90))
            objects_meta.append({"type": "signature", "bbox": {"x": sx, "y": sy, "width": sw, "height": sh}, "loc": "Bottom-Right"})

        else:  # Scholarship_Card_Stamp_Sig
            draw.text((60, 180), "State Scholarship Grant: Aadhaar & Identity Verification Application", fill=(10, 10, 10))
            draw.text((60, 215), "Please attach Aadhaar Card copy and obtain registrar endorsement.", fill=(50, 50, 50))
            # 1. Mock Card at Center (x=100, y=360, w=700, h=380)
            cx, cy, cw, ch = 100, 360, 700, 380
            draw.rectangle([cx, cy, cx + cw, cy + ch], fill=(255, 255, 255), outline=(120, 140, 170), width=3)
            # Tricolor
            draw.rectangle([cx + 3, cy + 3, cx + cw - 3, cy + 18], fill=(255, 153, 51))
            draw.rectangle([cx + 3, cy + 18, cx + cw - 3, cy + 33], fill=(255, 255, 255))
            draw.rectangle([cx + 3, cy + 33, cx + cw - 3, cy + 48], fill=(19, 136, 8))
            draw.text((cx + 20, cy + 55), "GOVERNMENT OF INDIA -- AADHAAR CARD", fill=(0, 0, 0))
            draw.text((cx + 20, cy + 85), f"Name: Candidate #{idx:02d} | DOB: 12/06/2004", fill=(30, 30, 30))
            draw.text((cx + 20, cy + 120), "4829  9912  4401", fill=(160, 10, 10))
            draw_photo_box(draw, cx + cw - 150, cy + 60, 120, 140, label="ID")
            objects_meta.append({"type": "id_card", "bbox": {"x": cx, "y": cy, "width": cw, "height": ch}, "loc": "Center"})

            # 2. Stamp at Bottom-Left
            st_cx, st_cy, rad = 180, 950, 60
            draw_official_stamp(draw, st_cx, st_cy, rad, ink_color=(180, 20, 20), text="SEALED")
            objects_meta.append({"type": "stamp", "bbox": {"x": st_cx - rad, "y": st_cy - rad, "width": rad * 2, "height": rad * 2}, "loc": "Bottom-Left"})

            # 3. Signature at Bottom-Right
            sx, sy, sw, sh = 580, 930, 250, 120
            draw.text((sx, sy - 20), "Applicant Signature:", fill=(60, 60, 60))
            draw_signature(draw, sx, sy, sw, sh, stroke_color=(20, 50, 160))
            objects_meta.append({"type": "signature", "bbox": {"x": sx, "y": sy, "width": sw, "height": sh}, "loc": "Bottom-Right"})

        save_p = DIR_COMPOSITES / fname
        doc.save(save_p, quality=94)
        gt[fname] = {
            "query_target": "multimodal composite",
            "category": "COMPOSITE",
            "combo_type": combo_type,
            "has_visual_match": True,
            "objects": objects_meta,
            "bbox": objects_meta[0]["bbox"]
        }
        print(f"  [Comp {idx:02d}/30] {fname} | Type: {combo_type} | Objects: {len(objects_meta)}")

    with open(DIR_COMPOSITES / "ground_truth_composites.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


# -----------------------------------------------------------------------------
# 4. Generate 15 Structured Hard Negative Documents
# -----------------------------------------------------------------------------
def generate_negatives():
    print("\n--- Generating 15 Hard Negative / Control Documents ---")
    gt = {}
    topics = [
        ("Digital Signature Disclaimer Circular", "This electronic memo is digitally generated and requires NO physical signature or ink endorsement."),
        ("Physical Stamp Exemption Notice", "As per revised university statutory norms, rubber stamps and wax seals are abolished for online marksheets."),
        ("No ID Card Submission Required", "Candidate admission verification is completed through national roll portal. Do NOT attach any physical ID card or Aadhaar copy."),
        ("Photograph Exemption Order", "Biometric camera recording was completed at gate. Physical passport photographs will NOT be accepted or pasted on this sheet."),
        ("Barcodes Discontinued Circular", "Old 1D barcodes and 2D matrix codes are discontinued in favor of cloud direct NFC tokenization."),
        ("Tuition Fee Regulatory Overview", "Details on annual undergraduate tuition schedules, hostel room tariffs, and refundable caution deposit structures."),
        ("Faculty Academic Senate Bylaws", "Rules governing quorum formation, amendment voting protocols, and executive dean advisory council meetings."),
        ("Campus Library Borrowing Terms", "Maximum borrowing quotas, book reservation queues, overdue fine rates, and inter-library loan protocols."),
        ("Annual Convocation Robe Guidelines", "Prescribed dress code, gown collection counters, guest invitation badges, and auditorium seating designations."),
        ("Laboratory Safety Code of Conduct", "Mandatory goggles, lab coat requirements, hazardous chemical disposal procedures, and emergency eyewash stations."),
        ("Gymnasium Facility Operating Hours", "Morning and evening workout batch slots, locker allocations, fitness equipment etiquette, and trainer schedules."),
        ("Hostel Vacation Guidelines", "Rules for room vacation before summer break, room inventory checks, key return desk, and luggage storage room."),
        ("Campus Canteen Price List", "Subsidized menu pricing for breakfast, lunch thali, evening tea snacks, and digital payment counters."),
        ("Parking Regulations for Two Wheelers", "Vehicle sticker registration, helmet requirements, speed limits within university campus roads, and designated bays."),
        ("Public Holiday Calendar 2026", "Official list of national holidays, festival breaks, term end dates, and administrative office working days.")
    ]

    for idx, (title, body) in enumerate(topics, 1):
        fname = f"doc_exp_negative_{idx:02d}.jpg"
        doc = Image.new("RGB", (900, 1200), color=(255, 255, 255))
        draw = ImageDraw.Draw(doc)
        draw.rectangle([25, 25, 875, 1175], outline=(180, 190, 205), width=2)

        draw.text((150, 50), "APEX UNIVERSITY ADMINISTRATIVE GAZETTE", fill=(15, 30, 80))
        draw.line([50, 95, 850, 95], fill=(20, 45, 95), width=2)
        draw.text((160, 130), title.upper(), fill=(20, 20, 20))

        lines = [
            body,
            "All students, teaching staff, and administrative departments are hereby directed to take note.",
            "This circular is issued under the authority of the Registrar and Academic Council.",
            "Issued at Pune University Campus on 15th January 2026."
        ]
        y_pos = 220
        for l in lines:
            draw.text((60, y_pos), l, fill=(40, 40, 40))
            y_pos += 60

        save_p = DIR_NEGATIVES / fname
        doc.save(save_p, quality=94)
        gt[fname] = {
            "query_target": "negative control",
            "category": "NEGATIVE_CONTROL",
            "has_visual_match": False,
            "visual_target": None,
            "bbox": None
        }
        print(f"  [Neg {idx:02d}/15] {fname} | Title: {title}")

    with open(DIR_NEGATIVES / "ground_truth_negatives.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


if __name__ == "__main__":
    generate_signatures()
    generate_stamps()
    generate_composites()
    generate_negatives()
    print("\n==========================================================================================")
    print("ALL EXPANDED DATASETS GENERATED SUCCESSFULLY (85 NEW DIVERSE DOCUMENTS)!")
    print("==========================================================================================")
