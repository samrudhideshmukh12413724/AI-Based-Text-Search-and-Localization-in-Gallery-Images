import io
import sys
from pathlib import Path
import cv2
from PIL import Image, ImageDraw

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from app.visual_region_extractor import get_visual_region_extractor

DATASET_DIR = ROOT_DIR.parent / "dataset" / "phase3b"
OUTPUT_DIR = ROOT_DIR.parent / "dataset" / "phase3b" / "annotated_proposals"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def test_visual_proposals():
    print("=" * 85)
    print("TESTING VISUAL REGION EXTRACTOR ON PHASE 3B BENCHMARK DATASET")
    print("=" * 85)

    extractor = get_visual_region_extractor()
    doc_files = sorted(DATASET_DIR.glob("*.jpg"))

    for doc_path in doc_files:
        regions = extractor.extract_regions(doc_path)
        print(f"\nDocument: {doc_path.name} -> Extracted {len(regions)} Visual Regions:")

        # Draw visualization image
        img = Image.open(doc_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        colors = {
            "qr_detector": (0, 229, 255),      # Cyan
            "contour_graphic": (236, 72, 153),  # Magenta/Pink
            "quadrant_anchor": (245, 158, 11),  # Amber
            "full_doc": (148, 163, 184)         # Slate
        }

        for i, reg in enumerate(regions):
            bx = reg.bbox
            src = reg.source
            loc = reg.location_desc
            print(f"  [{i+1:02d}] Source: {src:<16} | Loc: {loc:<12} | BBox: ({bx['x']:3d}, {bx['y']:3d}, {bx['width']:3d}, {bx['height']:3d})")

            if src != "full_doc":
                col = colors.get(src, (0, 255, 0))
                draw.rectangle([(bx["x"], bx["y"]), (bx["x"] + bx["width"], bx["y"] + bx["height"])], outline=col, width=3)
                draw.text((bx["x"] + 4, bx["y"] + 4), f"{src}:{loc}", fill=col)

        out_path = OUTPUT_DIR / f"proposals_{doc_path.name}"
        img.save(out_path, quality=90)
        print(f"  --> Saved visual proposal map to: {out_path.name}")

    print("\n" + "=" * 85)
    print("ALL REGION EXTRACTION INSPECTION MAPS GENERATED SUCCESSFULLY!")
    print("=" * 85)

if __name__ == "__main__":
    test_visual_proposals()
