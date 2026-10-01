"""Generates 60 general imagery, mixed media, and hard negative items to expand
the dataset to ~319 heterogeneous items across the 5 locked taxonomy pillars:
1. Animals (Cats, Dogs) - 10 items
2. Vehicles (Cars, Bicycles) - 10 items
3. Electronics/Devices (Laptops, Smartphones) - 10 items
4. Everyday Objects (Coffee Mugs, Books) - 10 items
5. Natural Scenery (Mountains, Landscapes) - 5 items
6. Mixed Media (Street Signs, Storefronts with Text) - 8 items
7. Hard Negative Controls (Abstract / Noise / Zero-Text) - 7 items
"""

import io
import math
import os
import random
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
DATASET_DIR = ROOT_DIR.parent / "dataset" / "general_expanded"
DATASET_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = ROOT_DIR.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

from app import database
from app.ocr import extract_text
from app.semantic_search import build_embeddings_index
from app.visual_search import get_visual_search_engine

def get_font(size=20):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

# -----------------------------------------------------------------------------
# Drawing Helpers for Iconic Recognizable Visual Categories
# -----------------------------------------------------------------------------

def draw_cat(draw, width, height, color_tone=(220, 140, 70)):
    # Background: cozy indoor rug/room
    draw.rectangle([0, 0, width, height], fill=(245, 240, 232))
    cx, cy = width // 2, height // 2 + 30
    
    # Body
    draw.ellipse([cx - 140, cy - 60, cx + 140, cy + 180], fill=color_tone, outline=(100, 60, 20), width=3)
    # Head
    draw.ellipse([cx - 110, cy - 170, cx + 110, cy + 10], fill=color_tone, outline=(100, 60, 20), width=3)
    # Pointed Ears
    draw.polygon([(cx - 95, cy - 120), (cx - 110, cy - 225), (cx - 35, cy - 160)], fill=color_tone, outline=(100, 60, 20))
    draw.polygon([(cx - 90, cy - 125), (cx - 100, cy - 210), (cx - 45, cy - 160)], fill=(255, 180, 180)) # inner ear
    draw.polygon([(cx + 95, cy - 120), (cx + 110, cy - 225), (cx + 35, cy - 160)], fill=color_tone, outline=(100, 60, 20))
    draw.polygon([(cx + 90, cy - 125), (cx + 100, cy - 210), (cx + 45, cy - 160)], fill=(255, 180, 180))
    # Eyes (almond shaped with pupils)
    draw.ellipse([cx - 65, cy - 105, cx - 20, cy - 70], fill=(90, 190, 60), outline=(20, 40, 10), width=2)
    draw.ellipse([cx - 47, cy - 103, cx - 38, cy - 72], fill=(10, 20, 5))
    draw.ellipse([cx + 20, cy - 105, cx + 65, cy - 70], fill=(90, 190, 60), outline=(20, 40, 10), width=2)
    draw.ellipse([cx + 38, cy - 103, cx + 47, cy - 72], fill=(10, 20, 5))
    # Nose & Mouth
    draw.polygon([(cx - 12, cy - 58), (cx + 12, cy - 58), (cx, cy - 44)], fill=(250, 140, 140))
    draw.line([cx, cy - 44, cx, cy - 30], fill=(60, 30, 10), width=2)
    draw.arc([cx - 24, cy - 36, cx, cy - 20], 0, 180, fill=(60, 30, 10), width=2)
    draw.arc([cx, cy - 36, cx + 24, cy - 20], 0, 180, fill=(60, 30, 10), width=2)
    # Whiskers
    for dy in [-15, 0, 15]:
        draw.line([cx - 40, cy - 40 + dy, cx - 170, cy - 45 + dy * 1.8], fill=(50, 30, 10), width=2)
        draw.line([cx + 40, cy - 40 + dy, cx + 170, cy - 45 + dy * 1.8], fill=(50, 30, 10), width=2)
    # Paws
    draw.ellipse([cx - 90, cy + 140, cx - 30, cy + 195], fill=(255, 245, 235), outline=(100, 60, 20), width=2)
    draw.ellipse([cx + 30, cy + 140, cx + 90, cy + 195], fill=(255, 245, 235), outline=(100, 60, 20), width=2)

def draw_dog(draw, width, height, color_tone=(160, 105, 50)):
    draw.rectangle([0, 0, width, height], fill=(235, 245, 235))
    cx, cy = width // 2, height // 2 + 25
    # Body
    draw.ellipse([cx - 150, cy - 40, cx + 150, cy + 190], fill=color_tone, outline=(70, 40, 15), width=3)
    # Head
    draw.ellipse([cx - 105, cy - 165, cx + 105, cy + 15], fill=color_tone, outline=(70, 40, 15), width=3)
    # Floppy Ears
    draw.ellipse([cx - 145, cy - 140, cx - 75, cy + 10], fill=(110, 65, 25), outline=(60, 30, 10), width=3)
    draw.ellipse([cx + 75, cy - 140, cx + 145, cy + 10], fill=(110, 65, 25), outline=(60, 30, 10), width=3)
    # Snout / Muzzle
    draw.ellipse([cx - 50, cy - 70, cx + 50, cy + 10], fill=(240, 220, 195), outline=(70, 40, 15), width=2)
    # Nose
    draw.ellipse([cx - 24, cy - 65, cx + 24, cy - 35], fill=(20, 20, 20))
    # Eyes
    draw.ellipse([cx - 65, cy - 110, cx - 30, cy - 75], fill=(40, 25, 10))
    draw.ellipse([cx - 50, cy - 102, cx - 42, cy - 94], fill=(255, 255, 255)) # highlight
    draw.ellipse([cx + 30, cy - 110, cx + 65, cy - 75], fill=(40, 25, 10))
    draw.ellipse([cx + 45, cy - 102, cx + 53, cy - 94], fill=(255, 255, 255))
    # Red Tongue
    draw.ellipse([cx - 15, cy - 15, cx + 15, cy + 25], fill=(240, 80, 95), outline=(180, 40, 50), width=1)

def draw_car(draw, width, height, body_color=(200, 30, 30)):
    # Background: asphalt street and sky
    draw.rectangle([0, 0, width, height // 2 + 40], fill=(210, 230, 250))
    draw.rectangle([0, height // 2 + 40, width, height], fill=(65, 70, 75))
    draw.line([0, height - 30, width, height - 30], fill=(250, 210, 30), width=6) # road stripe

    cx, cy = width // 2, height // 2 + 20
    # Car Body base
    draw.rounded_rectangle([cx - 280, cy - 10, cx + 280, cy + 90], radius=18, fill=body_color, outline=(20, 20, 20), width=3)
    # Cabin / Roof
    cabin_pts = [(cx - 170, cy - 10), (cx - 110, cy - 90), (cx + 110, cy - 90), (cx + 175, cy - 10)]
    draw.polygon(cabin_pts, fill=body_color, outline=(20, 20, 20))
    # Windows (front and rear)
    draw.polygon([(cx - 155, cy - 8), (cx - 102, cy - 80), (cx - 10, cy - 80), (cx - 10, cy - 8)], fill=(185, 225, 250), outline=(20, 20, 20), width=2)
    draw.polygon([(cx + 10, cy - 8), (cx + 10, cy - 80), (cx + 102, cy - 80), (cx + 160, cy - 8)], fill=(185, 225, 250), outline=(20, 20, 20), width=2)
    # Headlights & Taillights
    draw.rounded_rectangle([cx + 265, cy + 5, cx + 280, cy + 35], radius=5, fill=(255, 255, 140), outline=(20, 20, 20), width=2)
    draw.rounded_rectangle([cx - 280, cy + 5, cx - 265, cy + 35], radius=5, fill=(240, 30, 30), outline=(20, 20, 20), width=2)
    # Door Handle
    draw.rectangle([cx - 20, cy + 18, cx + 25, cy + 24], fill=(220, 220, 220), outline=(20, 20, 20))
    # Wheels (Rubber tire + metallic rim)
    for wx in [cx - 175, cx + 175]:
        draw.ellipse([wx - 55, cy + 45, wx + 55, cy + 155], fill=(30, 30, 35), outline=(10, 10, 10), width=3)
        draw.ellipse([wx - 32, cy + 68, wx + 32, cy + 132], fill=(210, 215, 220), outline=(50, 50, 50), width=2)
        draw.ellipse([wx - 10, cy + 90, wx + 10, cy + 110], fill=(40, 40, 40))

def draw_bicycle(draw, width, height, frame_color=(30, 120, 220)):
    draw.rectangle([0, 0, width, height], fill=(245, 248, 250))
    draw.line([0, height - 70, width, height - 70], fill=(120, 120, 120), width=4)
    cx, cy = width // 2, height // 2 + 10
    
    # Wheels
    r = 75
    w1_x = cx - 180
    w2_x = cx + 180
    wheel_y = cy + 45
    for wx in [w1_x, w2_x]:
        draw.ellipse([wx - r, wheel_y - r, wx + r, wheel_y + r], outline=(40, 40, 40), width=7)
        draw.ellipse([wx - r + 8, wheel_y - r + 8, wx + r - 8, wheel_y + r - 8], outline=(180, 180, 180), width=2)
        # Spokes
        for deg in range(0, 360, 45):
            rad = math.radians(deg)
            draw.line([wx, wheel_y, wx + (r - 10) * math.cos(rad), wheel_y + (r - 10) * math.sin(rad)], fill=(160, 160, 160), width=1)
        draw.ellipse([wx - 10, wheel_y - 10, wx + 10, wheel_y + 10], fill=(50, 50, 50))
    
    # Frame points: rear wheel, bottom bracket, seat, head tube, front wheel
    bb_x, bb_y = cx - 35, wheel_y
    seat_x, seat_y = cx - 65, cy - 50
    head_x, head_y = cx + 110, cy - 65
    
    # Tubes
    draw.line([w1_x, wheel_y, seat_x, seat_y], fill=frame_color, width=6) # seat stay
    draw.line([w1_x, wheel_y, bb_x, bb_y], fill=frame_color, width=6) # chain stay
    draw.line([bb_x, bb_y, seat_x, seat_y], fill=frame_color, width=6) # seat tube
    draw.line([bb_x, bb_y, head_x, head_y], fill=frame_color, width=6) # down tube
    draw.line([seat_x, seat_y, head_x, head_y], fill=frame_color, width=6) # top tube
    draw.line([head_x, head_y, w2_x, wheel_y], fill=frame_color, width=6) # fork
    
    # Seat
    draw.polygon([(seat_x - 35, seat_y - 22), (seat_x + 35, seat_y - 22), (seat_x + 15, seat_y - 12), (seat_x - 30, seat_y - 12)], fill=(30, 30, 30))
    draw.line([seat_x, seat_y, seat_x, seat_y - 16], fill=(160, 160, 160), width=5)
    # Handlebars
    draw.line([head_x, head_y, head_x + 10, head_y - 40], fill=(160, 160, 160), width=5)
    draw.arc([head_x - 15, head_y - 55, head_x + 35, head_y - 25], 180, 360, fill=(30, 30, 30), width=5)

def draw_laptop(draw, width, height):
    draw.rectangle([0, 0, width, height], fill=(235, 238, 245))
    cx, cy = width // 2, height // 2
    # Open Screen lid
    draw.rounded_rectangle([cx - 210, cy - 160, cx + 210, cy + 60], radius=10, fill=(40, 42, 48), outline=(15, 15, 20), width=3)
    # Screen Display Area (glowing code/graph dashboard)
    draw.rectangle([cx - 190, cy - 145, cx + 190, cy + 45], fill=(22, 27, 34))
    # Code snippet lines on display
    draw.rectangle([cx - 170, cy - 130, cx - 80, cy - 115], fill=(88, 166, 255))
    draw.rectangle([cx - 70, cy - 130, cx + 30, cy - 115], fill=(126, 231, 135))
    draw.rectangle([cx - 170, cy - 100, cx + 90, cy - 88], fill=(210, 168, 255))
    draw.rectangle([cx - 150, cy - 75, cx + 60, cy - 63], fill=(255, 166, 87))
    draw.rectangle([cx - 150, cy - 50, cx - 10, cy - 38], fill=(126, 231, 135))
    # Mini chart on right of display
    draw.rectangle([cx + 80, cy - 120, cx + 170, cy + 25], outline=(80, 90, 105), width=1)
    for bx, bh, bc in [(cx + 95, 45, (88, 166, 255)), (cx + 120, 75, (126, 231, 135)), (cx + 145, 95, (255, 123, 114))]:
        draw.rectangle([bx, cy + 20 - bh, bx + 16, cy + 20], fill=bc)
    # Keyboard Base (angled perspective)
    base_pts = [(cx - 260, cy + 130), (cx + 260, cy + 130), (cx + 215, cy + 60), (cx - 215, cy + 60)]
    draw.polygon(base_pts, fill=(180, 185, 195), outline=(70, 75, 85))
    # Keyboard Key Grid
    draw.polygon([(cx - 200, cy + 105), (cx + 200, cy + 105), (cx + 185, cy + 70), (cx - 185, cy + 70)], fill=(50, 52, 58))
    # Trackpad
    draw.rounded_rectangle([cx - 55, cy + 110, cx + 55, cy + 126], radius=3, fill=(150, 155, 165), outline=(100, 105, 115), width=1)

def draw_phone(draw, width, height):
    draw.rectangle([0, 0, width, height], fill=(240, 242, 245))
    cx, cy = width // 2, height // 2
    # Phone Body (modern curved chassis)
    draw.rounded_rectangle([cx - 110, cy - 210, cx + 110, cy + 210], radius=32, fill=(25, 28, 32), outline=(100, 105, 115), width=4)
    # Screen Display Area
    draw.rounded_rectangle([cx - 98, cy - 198, cx + 98, cy + 198], radius=24, fill=(15, 23, 42))
    # Dynamic Island / Camera punch-hole
    draw.rounded_rectangle([cx - 24, cy - 188, cx + 24, cy - 172], radius=8, fill=(0, 0, 0))
    # App Icons Grid
    icon_colors = [
        (59, 130, 246), (16, 185, 129), (249, 115, 22), (236, 72, 153),
        (168, 85, 247), (234, 179, 8), (14, 165, 233), (239, 68, 68),
        (99, 102, 241), (20, 184, 166), (244, 63, 94), (132, 204, 22)
    ]
    idx = 0
    for row in range(4):
        for col in range(3):
            ix = cx - 72 + col * 55
            iy = cy - 130 + row * 60
            draw.rounded_rectangle([ix, iy, ix + 36, iy + 36], radius=9, fill=icon_colors[idx % len(icon_colors)])
            idx += 1
    # Bottom Dock
    draw.rounded_rectangle([cx - 85, cy + 135, cx + 85, cy + 180], radius=14, fill=(30, 41, 59))
    for col in range(4):
        dx = cx - 68 + col * 40
        draw.rounded_rectangle([dx, cy + 144, dx + 26, cy + 170], radius=7, fill=icon_colors[(col + 2) % len(icon_colors)])

def draw_coffee_mug(draw, width, height):
    draw.rectangle([0, 0, width, height], fill=(248, 244, 238))
    cx, cy = width // 2 - 20, height // 2 + 20
    # Wooden Tabletop
    draw.rectangle([0, cy + 85, width, height], fill=(160, 105, 55))
    draw.line([0, cy + 85, width, cy + 85], fill=(110, 65, 25), width=3)
    
    # Handle on Right
    draw.arc([cx + 60, cy - 50, cx + 160, cy + 60], 270, 90, fill=(220, 50, 45), width=18)
    draw.arc([cx + 60, cy - 50, cx + 160, cy + 60], 270, 90, fill=(150, 25, 20), width=2)
    # Mug Body
    draw.rounded_rectangle([cx - 95, cy - 75, cx + 95, cy + 85], radius=14, fill=(235, 55, 50), outline=(160, 25, 20), width=3)
    # Coffee Surface Oval
    draw.ellipse([cx - 92, cy - 90, cx + 92, cy - 60], fill=(70, 40, 20), outline=(235, 55, 50), width=4)
    draw.ellipse([cx - 80, cy - 85, cx + 80, cy - 65], fill=(50, 25, 10))
    # Rising Steam lines
    for sx, offset in [(cx - 40, 0), (cx, -15), (cx + 40, 10)]:
        pts = []
        for t in range(0, 70, 4):
            rad = math.radians(t * 7)
            pts.append((sx + math.sin(rad) * 12, cy - 100 - t + offset))
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=(195, 195, 205), width=3)

def draw_book(draw, width, height):
    draw.rectangle([0, 0, width, height], fill=(245, 245, 245))
    cx, cy = width // 2, height // 2 + 10
    # Open Book Hardcover base
    draw.polygon([(cx, cy + 70), (cx - 220, cy + 40), (cx - 230, cy - 80), (cx, cy - 50)], fill=(30, 60, 120))
    draw.polygon([(cx, cy + 70), (cx + 220, cy + 40), (cx + 230, cy - 80), (cx, cy - 50)], fill=(30, 60, 120))
    # Left Pages
    draw.polygon([(cx, cy + 60), (cx - 210, cy + 30), (cx - 215, cy - 85), (cx, cy - 55)], fill=(255, 252, 245), outline=(180, 175, 160), width=2)
    # Right Pages
    draw.polygon([(cx, cy + 60), (cx + 210, cy + 30), (cx + 215, cy - 85), (cx, cy - 55)], fill=(255, 252, 245), outline=(180, 175, 160), width=2)
    # Text Lines on Pages
    for line_y in range(cy - 60, cy + 40, 16):
        draw.line([cx - 195, line_y, cx - 25, line_y - 5], fill=(120, 120, 125), width=2)
        draw.line([cx + 25, line_y - 5, cx + 195, line_y], fill=(120, 120, 125), width=2)
    # Center Ribbon Bookmark
    draw.line([cx, cy - 55, cx, cy + 90], fill=(220, 30, 40), width=4)

def draw_mountain(draw, width, height):
    # Gradient Sky
    draw.rectangle([0, 0, width, height // 2], fill=(175, 215, 245))
    draw.rectangle([0, height // 2, width, height], fill=(95, 145, 85))
    # Sun
    draw.ellipse([width - 160, 40, width - 80, 120], fill=(255, 220, 60))
    # Distant Mountains (Dark slate)
    draw.polygon([(40, height // 2 + 40), (220, 110), (420, height // 2 + 40)], fill=(110, 125, 140))
    draw.polygon([(260, height // 2 + 40), (480, 80), (700, height // 2 + 40)], fill=(90, 105, 125))
    draw.polygon([(520, height // 2 + 40), (660, 140), (820, height // 2 + 40)], fill=(110, 125, 140))
    # Snowcaps
    draw.polygon([(220, 110), (185, 165), (210, 155), (235, 165), (255, 160)], fill=(255, 255, 255))
    draw.polygon([(480, 80), (435, 145), (465, 135), (500, 150), (525, 140)], fill=(255, 255, 255))
    # Pine Trees in foreground
    for tx in range(60, width - 60, 85):
        ty = height // 2 + 30 + (tx % 30)
        draw.polygon([(tx, ty - 55), (tx - 25, ty), (tx + 25, ty)], fill=(35, 80, 40))
        draw.polygon([(tx, ty - 35), (tx - 32, ty + 25), (tx + 32, ty + 25)], fill=(30, 70, 35))
        draw.rectangle([tx - 5, ty + 25, tx + 5, ty + 45], fill=(80, 50, 25))

def draw_street_sign(draw, width, height, sign_type="STOP"):
    draw.rectangle([0, 0, width, height], fill=(210, 230, 245)) # sky
    cx, cy = width // 2, height // 2 - 30
    # Metal Pole
    draw.rectangle([cx - 10, cy, cx + 10, height - 20], fill=(160, 165, 175), outline=(90, 95, 105), width=2)
    
    if sign_type == "STOP":
        # Octagon Stop sign
        r = 140
        pts = []
        for i in range(8):
            deg = 45 * i + 22.5
            rad = math.radians(deg)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
        draw.polygon(pts, fill=(215, 25, 25), outline=(255, 255, 255), width=6)
        draw.text((cx - 78, cy - 35), "STOP", fill=(255, 255, 255), font=get_font(52))
    elif sign_type == "SPEED":
        # Yellow Diamond Speed sign
        r = 135
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        draw.polygon(pts, fill=(255, 215, 0), outline=(20, 20, 20), width=6)
        draw.text((cx - 65, cy - 45), "SPEED", fill=(20, 20, 20), font=get_font(28))
        draw.text((cx - 55, cy - 10), "LIMIT", fill=(20, 20, 20), font=get_font(28))
        draw.text((cx - 35, cy + 25), "50", fill=(20, 20, 20), font=get_font(36))
    else:  # PARKING
        # Blue Square Parking
        draw.rounded_rectangle([cx - 120, cy - 120, cx + 120, cy + 120], radius=14, fill=(20, 90, 200), outline=(255, 255, 255), width=6)
        draw.text((cx - 40, cy - 70), "P", fill=(255, 255, 255), font=get_font(100))
        draw.text((cx - 65, cy + 45), "PARKING", fill=(255, 255, 255), font=get_font(24))

def draw_storefront(draw, width, height, store_name="CITY CAFE & BAKERY"):
    # Street & Building Facade
    draw.rectangle([0, 0, width, height], fill=(225, 220, 210))
    # Striped Awning
    awning_y = 110
    draw.rectangle([60, awning_y, width - 60, awning_y + 80], fill=(200, 40, 40))
    for ax in range(60, width - 60, 45):
        draw.rectangle([ax, awning_y, ax + 22, awning_y + 80], fill=(255, 255, 255))
    # Store Sign Banner
    draw.rectangle([70, 30, width - 70, 95], fill=(30, 40, 60), outline=(210, 180, 100), width=3)
    draw.text((width // 2 - 160, 45), store_name, fill=(255, 225, 120), font=get_font(24))
    # Glass Windows and Door
    win_y = awning_y + 95
    # Left Window
    draw.rectangle([90, win_y, 320, win_y + 220], fill=(180, 220, 240), outline=(60, 60, 60), width=3)
    # Glass Door (Center)
    draw.rectangle([360, win_y, 520, height - 10], fill=(200, 230, 245), outline=(60, 60, 60), width=4)
    draw.rectangle([500, win_y + 100, 510, win_y + 140], fill=(220, 180, 50)) # handle
    # Right Window
    draw.rectangle([560, win_y, 790, win_y + 220], fill=(180, 220, 240), outline=(60, 60, 60), width=3)

def draw_abstract_negative(draw, width, height, pattern="geometric"):
    if pattern == "circles":
        draw.rectangle([0, 0, width, height], fill=(240, 240, 245))
        for r in range(40, 380, 35):
            draw.ellipse([width // 2 - r, height // 2 - r, width // 2 + r, height // 2 + r], outline=(180, 190, 205), width=2)
    elif pattern == "gradient":
        for y in range(height):
            ratio = y / height
            c = int(220 + 30 * ratio)
            draw.line([0, y, width, y], fill=(c, c - 10, c + 5))
    else: # grid noise
        draw.rectangle([0, 0, width, height], fill=(235, 235, 235))
        for x in range(0, width, 40):
            draw.line([x, 0, x, height], fill=(210, 210, 215), width=1)
        for y in range(0, height, 40):
            draw.line([0, y, width, y], fill=(210, 210, 215), width=1)

# -----------------------------------------------------------------------------
# Master Generation & Ingestion Function
# -----------------------------------------------------------------------------

def generate_and_ingest():
    v_engine = get_visual_search_engine()
    
    print("=" * 90)
    print("EXPANDING CORPUS: GENERATING 60 GENERAL IMAGES, MIXED MEDIA & HARD NEGATIVES")
    print("=" * 90)
    
    W, H = 880, 580
    items_to_create = []
    
    # 1. Cats (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_animal_cat_{i:02d}.jpg",
            "category": "GENERAL_ANIMAL",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_cat(d, w, h, (220, 140, 70) if i % 2 == 0 else (160, 160, 165)),
            "is_neg": False
        })
    
    # 2. Dogs (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_animal_dog_{i:02d}.jpg",
            "category": "GENERAL_ANIMAL",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_dog(d, w, h, (160, 105, 50) if i % 2 == 0 else (210, 180, 130)),
            "is_neg": False
        })

    # 3. Cars (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_vehicle_car_{i:02d}.jpg",
            "category": "GENERAL_VEHICLE",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_car(d, w, h, (200, 30, 30) if i % 2 == 0 else (30, 100, 200)),
            "is_neg": False
        })

    # 4. Bicycles (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_vehicle_bicycle_{i:02d}.jpg",
            "category": "GENERAL_VEHICLE",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_bicycle(d, w, h, (30, 120, 220) if i % 2 == 0 else (210, 50, 40)),
            "is_neg": False
        })

    # 5. Laptops (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_device_laptop_{i:02d}.jpg",
            "category": "GENERAL_DEVICE",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_laptop(d, w, h),
            "is_neg": False
        })

    # 6. Smartphones (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_device_phone_{i:02d}.jpg",
            "category": "GENERAL_DEVICE",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_phone(d, w, h),
            "is_neg": False
        })

    # 7. Coffee Mugs (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_object_coffee_{i:02d}.jpg",
            "category": "GENERAL_OBJECT",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_coffee_mug(d, w, h),
            "is_neg": False
        })

    # 8. Books (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_object_book_{i:02d}.jpg",
            "category": "GENERAL_OBJECT",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_book(d, w, h),
            "is_neg": False
        })

    # 9. Mountains / Landscapes (5)
    for i in range(1, 6):
        items_to_create.append({
            "fname": f"general_scenery_mountain_{i:02d}.jpg",
            "category": "GENERAL_SCENERY",
            "text": "(no text detected)",
            "drawer": lambda d, w, h: draw_mountain(d, w, h),
            "is_neg": False
        })

    # 10. Mixed Street Signs with text (4)
    sign_configs = [("STOP", "STOP"), ("SPEED", "SPEED LIMIT 50"), ("PARKING", "P PARKING"), ("STOP", "STOP SIGN AHEAD")]
    for i, (stype, stext) in enumerate(sign_configs, 1):
        items_to_create.append({
            "fname": f"mixed_streetsign_{i:02d}.jpg",
            "category": "MIXED_MEDIA",
            "text": stext,
            "drawer": lambda d, w, h, s=stype: draw_street_sign(d, w, h, s),
            "is_neg": False
        })

    # 11. Mixed Storefronts with text (4)
    store_configs = ["CITY CAFE & BAKERY", "TECH BOOKS & STATIONERY", "CAMPUS COFFEE SHOP", "METRO PHARMACY"]
    for i, sname in enumerate(store_configs, 1):
        items_to_create.append({
            "fname": f"mixed_storefront_{i:02d}.jpg",
            "category": "MIXED_MEDIA",
            "text": sname,
            "drawer": lambda d, w, h, s=sname: draw_storefront(d, w, h, s),
            "is_neg": False
        })

    # 12. Hard Negatives (Abstract patterns, noise, zero-text) (7)
    neg_types = ["circles", "gradient", "grid", "circles", "gradient", "grid", "circles"]
    for i, ntype in enumerate(neg_types, 1):
        items_to_create.append({
            "fname": f"negative_abstract_{i:02d}.jpg",
            "category": "NEGATIVE_CONTROL",
            "text": "(no text detected)",
            "drawer": lambda d, w, h, p=ntype: draw_abstract_negative(d, w, h, p),
            "is_neg": True
        })

    total_added = 0
    total_regions = 0
    
    for idx, item in enumerate(items_to_create, 1):
        t0 = time.time()
        img = Image.new("RGB", (W, H), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        item["drawer"](draw, W, H)
        
        # Save to dataset and backend uploads
        d_path = DATASET_DIR / item["fname"]
        u_path = UPLOADS_DIR / item["fname"]
        img.save(d_path, quality=95)
        img.save(u_path, quality=95)
        
        # Ingest to database
        saved = database.save_image(
            image_name=item["fname"],
            image_path=str(u_path.resolve()),
            extracted_text=item["text"],
            original_ocr_text=item["text"],
            cleaned_text=item["text"],
            category=item["category"],
            has_visual_objects=0 if item["is_neg"] else 1,
            visual_metadata={"category": item["category"]},
        )
        img_id = saved["id"]
        
        reg_count = 0
        if not item["is_neg"]:
            reg_count = v_engine.index_document(img_id, item["fname"], str(u_path.resolve()))
            total_regions += reg_count
        
        dt = time.time() - t0
        total_added += 1
        print(f"  [{idx:02d}/{len(items_to_create)}] {item['fname']} | Cat: {item['category']} | Regions: {reg_count} ({dt:.2f}s)")

    print("\nRefreshing Dense Semantic MiniLM Vector Index...")
    build_embeddings_index()
    
    print("\n" + "=" * 90)
    print(f"SUCCESS: Added {total_added} new items with {total_regions} visual regions!")
    print(f"Total documents currently in DB: {len(database.list_images())}")
    print("=" * 90)

if __name__ == "__main__":
    generate_and_ingest()
