"""Visual Region Extractor for Phase 3B: Proposes candidate visual sub-regions inside document images."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from app.visual_detector import get_visual_detector


@dataclass
class VisualRegion:
    crop_image: Image.Image
    bbox: dict  # {"x": int, "y": int, "width": int, "height": int}
    normalized_bbox: dict  # {"x": float, "y": float, "width": float, "height": float}
    source: str  # "qr_detector", "contour_graphic", "color_region", "quadrant_anchor", "full_doc"
    location_desc: str


def _get_location_desc(x: float, y: float, w: float, h: float) -> str:
    cx, cy = x + w / 2, y + h / 2
    if w >= 0.85 and h >= 0.85:
        return "Full Document"
    horiz = "Left" if cx < 0.35 else "Right" if cx > 0.65 else "Center"
    vert = "Top" if cy < 0.35 else "Bottom" if cy > 0.65 else "Middle"
    return f"{vert}-{horiz}" if horiz != "Center" or vert != "Middle" else "Center"


def _compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH

    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    unionArea = boxAArea + boxBArea - interArea

    return interArea / unionArea if unionArea > 0 else 0.0


class VisualRegionExtractor:
    """Extracts candidate visual sub-regions from a document image."""

    def __init__(self):
        self.qr_detector = get_visual_detector()

    def extract_regions(self, image_input) -> List[VisualRegion]:
        """
        Extracts candidate visual crops and bounding boxes from an image file or numpy array.
        Returns a list of VisualRegion objects.
        """
        if isinstance(image_input, (str, Path)):
            img_path = str(image_input)
            img_cv = cv2.imread(img_path)
            if img_cv is None:
                raise ValueError(f"Could not load image from {img_path}")
            img_pil = Image.open(img_path).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            img_cv = image_input
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
        else:
            raise TypeError("Expected image path or numpy ndarray")

        H, W = img_cv.shape[:2]
        candidate_boxes = []  # List of (x, y, w, h, source)

        # ---------------------------------------------------------------------
        # 1. Structured Visual Objects (QR / Barcode detector)
        # ---------------------------------------------------------------------
        vis_res = self.qr_detector.detect_visual_objects(img_cv)
        for obj in vis_res.get("objects", []):
            bx = obj["bbox"]
            pad = 12
            x = max(0, bx["x"] - pad)
            y = max(0, bx["y"] - pad)
            w = min(W - x, bx["width"] + pad * 2)
            h = min(H - y, bx["height"] + pad * 2)
            candidate_boxes.append((x, y, w, h, "qr_detector"))

        # ---------------------------------------------------------------------
        # 2. Color Block Detection (Photographs, Color Badges, Stamps)
        # ---------------------------------------------------------------------
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        # Detect rich color regions excluding white background and dark black text
        color_mask = cv2.inRange(hsv, np.array([0, 35, 40]), np.array([180, 255, 255]))
        color_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        color_dilated = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, color_kernel)

        color_contours, _ = cv2.findContours(color_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in color_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area > 4000 and w >= 50 and h >= 50 and (w < W * 0.90 or h < H * 0.50):
                # Avoid full-width banner
                if w < W * 0.80 or h > 60:
                    pad = 10
                    px = max(0, x - pad)
                    py = max(0, y - pad)
                    pw = min(W - px, w + pad * 2)
                    ph = min(H - py, h + pad * 2)
                    candidate_boxes.append((px, py, pw, ph, "color_region"))

        # ---------------------------------------------------------------------
        # 2B. Saturated Color Regions (Vibrant Objects on Non-White Grounds)
        # ---------------------------------------------------------------------
        # Captures localized, highly saturated objects (e.g. blue car, red stamp,
        # smartphone display) even when surrounded by non-white table or road backgrounds.
        _, s_chan, _ = cv2.split(hsv)
        sat_mask = (s_chan > 65).astype(np.uint8) * 255
        sat_dilated = cv2.morphologyEx(sat_mask, cv2.MORPH_CLOSE, color_kernel)
        cnts_sat, _ = cv2.findContours(sat_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts_sat:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if 4000 < area < (W * H * 0.70) and w >= 50 and h >= 50 and w < W * 0.85 and h < H * 0.80:
                aspect = w / max(1, h)
                if 0.22 <= aspect <= 4.5:
                    pad = 10
                    px = max(0, x - pad)
                    py = max(0, y - pad)
                    pw = min(W - px, w + pad * 2)
                    ph = min(H - py, h + pad * 2)
                    candidate_boxes.append((px, py, pw, ph, "color_region"))

        # ---------------------------------------------------------------------
        # 3. OpenCV Edge Gradient Contour Regions (Signatures, Stamps, Logos)
        # ---------------------------------------------------------------------
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
        abs_grad = cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0)
        _, edge_mask = cv2.threshold(abs_grad, 50, 255, cv2.THRESH_BINARY)

        edge_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 15))
        edge_dilated = cv2.dilate(edge_mask, edge_kernel, iterations=1)

        edge_contours, _ = cv2.findContours(edge_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in edge_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            # Signatures / Stamps / Graphical shapes
            if area > 3500 and w >= 55 and h >= 35 and (w < W * 0.70 and h < H * 0.35):
                aspect = w / max(1, h)
                if 0.20 < aspect < 5.5:
                    pad = 10
                    px = max(0, x - pad)
                    py = max(0, y - pad)
                    pw = min(W - px, w + pad * 2)
                    ph = min(H - py, h + pad * 2)
                    candidate_boxes.append((px, py, pw, ph, "contour_graphic"))

        # ---------------------------------------------------------------------
        # 3B. Embedded Card & Rectangular Enclosure Detection (Aadhaar, ID Cards)
        # ---------------------------------------------------------------------
        # Detect card border outlines and bounded enclosures inside forms
        card_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 25))
        card_dilated = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, card_kernel)
        card_contours, _ = cv2.findContours(card_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in card_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            aspect = w / max(1, h)
            # Standard ID/Aadhaar cards have aspect ratio ~1.35 to 1.85 and span 10% to 55% of document
            if (0.30 * W <= w <= 0.90 * W) and (0.15 * H <= h <= 0.50 * H):
                if 1.10 <= aspect <= 2.20 and area > (W * H * 0.06):
                    pad = 8
                    px = max(0, x - pad)
                    py = max(0, y - pad)
                    pw = min(W - px, w + pad * 2)
                    ph = min(H - py, h + pad * 2)
                    candidate_boxes.append((px, py, pw, ph, "card_enclosure"))

        # ---------------------------------------------------------------------
        # 3C. Baseline-Cleaned Edge Contour Proposals (Objects on Surfaces / Tables)
        # ---------------------------------------------------------------------
        # Suppress long continuous horizontal divider lines that touch image borders
        # (e.g. tabletop edges, road baselines) before dilation so they don't merge
        # with objects sitting on them (e.g. coffee mug). Internal object baselines
        # (e.g. laptop base) that do not touch borders are preserved intact.
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(W * 0.30), 1))
        long_h = cv2.morphologyEx(edge_mask, cv2.MORPH_OPEN, h_kernel)
        h_cnts, _ = cv2.findContours(long_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        border_mask = np.zeros_like(edge_mask)
        for c in h_cnts:
            bx, by, bw, bh = cv2.boundingRect(c)
            if (bx <= int(W * 0.05)) or ((bx + bw) >= int(W * 0.95)):
                cv2.drawContours(border_mask, [c], -1, 255, -1)

        border_dil = cv2.dilate(border_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)), iterations=1)
        em_cleaned = cv2.subtract(edge_mask, border_dil)

        fine_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        fine_dilated = cv2.dilate(em_cleaned, fine_kernel, iterations=1)
        fine_contours, _ = cv2.findContours(fine_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in fine_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if 2500 < area < (W * H * 0.65) and w >= 45 and h >= 45:
                if w <= W * 0.85 and h <= H * 0.75:
                    aspect = w / max(1, h)
                    if 0.22 <= aspect <= 4.2:
                        pad = 10
                        px = max(0, x - pad)
                        py = max(0, y - pad)
                        pw = min(W - px, w + pad * 2)
                        ph = min(H - py, h + pad * 2)
                        candidate_boxes.append((px, py, pw, ph, "fine_contour"))

        # ---------------------------------------------------------------------
        # 4. Spatial Layout Quadrant & Card Anchors
        # ---------------------------------------------------------------------
        anchors = [
            # Top-Right (Photo / ID Badge zone: x: 65-95%, y: 10-35%)
            (int(W * 0.68), int(H * 0.10), int(W * 0.26), int(H * 0.22), "quadrant_anchor"),
            # Bottom-Right (Signature zone: x: 60-95%, y: 72-92%)
            (int(W * 0.62), int(H * 0.72), int(W * 0.32), int(H * 0.18), "quadrant_anchor"),
            # Bottom-Left (Official Stamp zone: x: 5-35%, y: 70-92%)
            (int(W * 0.06), int(H * 0.70), int(W * 0.30), int(H * 0.20), "quadrant_anchor"),
            # Mid-Page Card Proposal (Embedded ID / Aadhaar card slot)
            (int(W * 0.08), int(H * 0.35), int(W * 0.84), int(H * 0.33), "card_proposal"),
            # Lower-Page Card Proposal (Attachment slot)
            (int(W * 0.08), int(H * 0.52), int(W * 0.84), int(H * 0.35), "card_proposal"),
            # Full Document (Global context)
            (0, 0, W, H, "full_doc"),
        ]
        candidate_boxes.extend(anchors)

        # ---------------------------------------------------------------------
        # 5. Deduplication & NMS (IoU Suppression)
        # ---------------------------------------------------------------------
        priority_order = {
            "qr_detector": 0,
            "color_region": 1,
            "card_enclosure": 2,
            "contour_graphic": 3,
            "fine_contour": 4,
            "card_proposal": 5,
            "quadrant_anchor": 6,
            "full_doc": 7,
        }
        candidate_boxes.sort(key=lambda b: priority_order.get(b[4], 99))

        filtered_boxes = []
        for box in candidate_boxes:
            x, y, w, h, src = box
            if src != "full_doc":
                overlap = False
                for f in filtered_boxes:
                    if f[4] != "full_doc":
                        # Do not suppress fine-grained sub-elements (qr, photo, signature) by containing card
                        is_card_pair = ("card" in src and "card" not in f[4]) or ("card" not in src and "card" in f[4])
                        threshold = 0.85 if is_card_pair else 0.60
                        if _compute_iou((x, y, w, h), (f[0], f[1], f[2], f[3])) > threshold:
                            overlap = True
                            break
                if overlap:
                    continue
            filtered_boxes.append(box)

        # ---------------------------------------------------------------------
        # 6. Build VisualRegion Objects
        # ---------------------------------------------------------------------
        regions = []
        for x, y, w, h, src in filtered_boxes:
            crop = img_pil.crop((x, y, x + w, y + h))
            norm_x = round(x / W, 4)
            norm_y = round(y / H, 4)
            norm_w = round(w / W, 4)
            norm_h = round(h / H, 4)
            loc_desc = _get_location_desc(norm_x, norm_y, norm_w, norm_h)

            regions.append(
                VisualRegion(
                    crop_image=crop,
                    bbox={"x": x, "y": y, "width": w, "height": h},
                    normalized_bbox={"x": norm_x, "y": norm_y, "width": norm_w, "height": norm_h},
                    source=src,
                    location_desc=loc_desc,
                )
            )

        return regions


_extractor = None


def get_visual_region_extractor() -> VisualRegionExtractor:
    global _extractor
    if _extractor is None:
        _extractor = VisualRegionExtractor()
    return _extractor
