"""
Visual Object & Sub-Image Detector (Phase 3).
Specialized for detecting, localizing, and decoding visual sub-elements (QR codes, barcodes, stamps)
embedded inside larger document images using OpenCV.
"""

from pathlib import Path
from typing import Any
import cv2
import numpy as np


def _determine_location_desc(x: int, y: int, w: int, h: int, img_w: int, img_h: int) -> str:
    """Classify the bounding box location into human-readable document quadrants."""
    cx = x + w / 2.0
    cy = y + h / 2.0

    # Vertical position
    if cy < img_h * 0.33:
        v_pos = "Top"
    elif cy > img_h * 0.66:
        v_pos = "Bottom"
    else:
        v_pos = "Center"

    # Horizontal position
    if cx < img_w * 0.33:
        h_pos = "Left"
    elif cx > img_w * 0.66:
        h_pos = "Right"
    else:
        h_pos = "Center"

    if v_pos == "Center" and h_pos == "Center":
        return "Center"
    return f"{v_pos}-{h_pos}"


class VisualDetector:
    """OpenCV-based Visual Sub-Image and QR Code Detector."""

    def __init__(self):
        self.qr_detector = cv2.QRCodeDetector()

    def detect_visual_objects(self, image_input: str | Path | np.ndarray) -> dict[str, Any]:
        """
        Detects all visual sub-objects (e.g. QR codes) inside the given image.
        
        Returns:
            dict containing:
                - detected: bool
                - type: str
                - count: int
                - objects: list of detected objects with bounding boxes, normalized coordinates, and data.
                - image_dimensions: { width, height }
        """
        if isinstance(image_input, (str, Path)):
            img_path = str(image_input)
            img = cv2.imread(img_path)
            if img is None:
                raise ValueError(f"Could not load image from path: {img_path}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise TypeError("image_input must be a file path or numpy ndarray")

        img_h, img_w = img.shape[:2]

        # Multi-stage detection pipeline:
        # Stage 1: Standard RGB / BGR detection
        # Stage 2: Grayscale + CLAHE contrast enhancement
        # Stage 3: Adaptive thresholding for difficult/low-contrast samples
        detected_objects = self._run_multi_qr_detection(img)

        # If standard detection found nothing, try enhanced grayscale
        if not detected_objects:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            detected_objects = self._run_multi_qr_detection(enhanced)

        # If still nothing, try thresholding
        if not detected_objects:
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            detected_objects = self._run_multi_qr_detection(thresh)

        # Stage 4: Multi-scale upscaling (for small embedded QR codes)
        if not detected_objects:
            # Upscale 1.75x for tiny sub-elements
            upscaled = cv2.resize(img, None, fx=1.75, fy=1.75, interpolation=cv2.INTER_CUBIC)
            raw_upscaled_objs = self._run_multi_qr_detection(upscaled)
            # Map coordinates back to original scale
            for uobj in raw_upscaled_objs:
                ubox = uobj["bbox"]
                orig_x = int(round(ubox["x"] / 1.75))
                orig_y = int(round(ubox["y"] / 1.75))
                orig_w = int(round(ubox["width"] / 1.75))
                orig_h = int(round(ubox["height"] / 1.75))
                detected_objects.append({
                    "label": "QR Code",
                    "type": "qr_code",
                    "bbox": {"x": orig_x, "y": orig_y, "width": orig_w, "height": orig_h},
                    "normalized_bbox": {
                        "x": round(orig_x / img_w, 4),
                        "y": round(orig_y / img_h, 4),
                        "width": round(orig_w / img_w, 4),
                        "height": round(orig_h / img_h, 4),
                    },
                    "data": uobj.get("data", ""),
                    "location_desc": _determine_location_desc(orig_x, orig_y, orig_w, orig_h, img_w, img_h),
                    "confidence": "Detected (Multi-Scale)",
                })

        # Deduplicate overlapping bounding boxes (if any)
        unique_objects = self._deduplicate_boxes(detected_objects)

        return {
            "detected": len(unique_objects) > 0,
            "type": "qr_code" if len(unique_objects) > 0 else "none",
            "count": len(unique_objects),
            "objects": unique_objects,
            "image_dimensions": {"width": img_w, "height": img_h},
        }

    def _run_multi_qr_detection(self, img_bgr_or_gray: np.ndarray) -> list[dict[str, Any]]:
        """Run OpenCV QR detector on an image array."""
        img_h, img_w = img_bgr_or_gray.shape[:2]
        results = []

        try:
            # detectAndDecodeMulti finds multiple QR codes simultaneously
            retval, decoded_info, points, _ = self.qr_detector.detectAndDecodeMulti(img_bgr_or_gray)
            
            if retval and points is not None and len(points) > 0:
                for idx, pts in enumerate(points):
                    # pts is a 4x2 array of corner points: [ [x1, y1], [x2, y2], [x3, y3], [x4, y4] ]
                    pts_int = pts.astype(int)
                    x_min = int(np.min(pts_int[:, 0]))
                    y_min = int(np.min(pts_int[:, 1]))
                    x_max = int(np.max(pts_int[:, 0]))
                    y_max = int(np.max(pts_int[:, 1]))

                    w = max(1, x_max - x_min)
                    h = max(1, y_max - y_min)

                    # Clamp to image boundaries
                    x_min = max(0, min(x_min, img_w - 1))
                    y_min = max(0, min(y_min, img_h - 1))
                    w = min(w, img_w - x_min)
                    h = min(h, img_h - y_min)

                    data_str = decoded_info[idx] if idx < len(decoded_info) else ""
                    loc_desc = _determine_location_desc(x_min, y_min, w, h, img_w, img_h)

                    results.append({
                        "label": "QR Code",
                        "type": "qr_code",
                        "bbox": {
                            "x": x_min,
                            "y": y_min,
                            "width": w,
                            "height": h,
                        },
                        "normalized_bbox": {
                            "x": round(x_min / img_w, 4),
                            "y": round(y_min / img_h, 4),
                            "width": round(w / img_w, 4),
                            "height": round(h / img_h, 4),
                        },
                        "data": data_str,
                        "location_desc": loc_desc,
                        "confidence": "Detected",
                    })
        except Exception:
            # Fallback to single QR detectAndDecode if multi fails
            try:
                data_str, pts, _ = self.qr_detector.detectAndDecode(img_bgr_or_gray)
                if pts is not None and len(pts) > 0:
                    pts_int = pts[0].astype(int)
                    x_min = int(np.min(pts_int[:, 0]))
                    y_min = int(np.min(pts_int[:, 1]))
                    x_max = int(np.max(pts_int[:, 0]))
                    y_max = int(np.max(pts_int[:, 1]))
                    w = max(1, x_max - x_min)
                    h = max(1, y_max - y_min)
                    x_min = max(0, min(x_min, img_w - 1))
                    y_min = max(0, min(y_min, img_h - 1))
                    w = min(w, img_w - x_min)
                    h = min(h, img_h - y_min)
                    loc_desc = _determine_location_desc(x_min, y_min, w, h, img_w, img_h)

                    results.append({
                        "label": "QR Code",
                        "type": "qr_code",
                        "bbox": {"x": x_min, "y": y_min, "width": w, "height": h},
                        "normalized_bbox": {
                            "x": round(x_min / img_w, 4),
                            "y": round(y_min / img_h, 4),
                            "width": round(w / img_w, 4),
                            "height": round(h / img_h, 4),
                        },
                        "data": data_str,
                        "location_desc": loc_desc,
                        "confidence": "Detected",
                    })
            except Exception:
                pass

        return results

    def _deduplicate_boxes(self, objects: list[dict[str, Any]], iou_threshold: float = 0.5) -> list[dict[str, Any]]:
        """Remove duplicate detections of the same object."""
        if not objects:
            return []

        unique = []
        for obj in objects:
            b1 = obj["bbox"]
            is_dup = False
            for u in unique:
                b2 = u["bbox"]
                # Calculate IoU between b1 and b2
                ix1 = max(b1["x"], b2["x"])
                iy1 = max(b1["y"], b2["y"])
                ix2 = min(b1["x"] + b1["width"], b2["x"] + b2["width"])
                iy2 = min(b1["y"] + b1["height"], b2["y"] + b2["height"])

                inter_w = max(0, ix2 - ix1)
                inter_h = max(0, iy2 - iy1)
                inter_area = inter_w * inter_h

                area1 = b1["width"] * b1["height"]
                area2 = b2["width"] * b2["height"]
                union_area = area1 + area2 - inter_area

                if union_area > 0 and (inter_area / union_area) > iou_threshold:
                    is_dup = True
                    break

            if not is_dup:
                unique.append(obj)

        return unique

    def draw_annotated_image(self, image_input: str | Path | np.ndarray, detected_result: dict[str, Any]) -> np.ndarray:
        """
        Draws bounding box rectangles, corner accents, and labels on the image for visual verification.
        """
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input.copy()

        for obj in detected_result.get("objects", []):
            bbox = obj["bbox"]
            x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]

            # Main bounding box in vibrant Cyan/Blue (BGR: 255, 180, 0)
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 180, 0), 3)

            # Draw highlighted corner brackets
            corner_len = min(20, w // 4, h // 4)
            # Top-left
            cv2.line(img, (x, y), (x + corner_len, y), (0, 255, 255), 5)
            cv2.line(img, (x, y), (x, y + corner_len), (0, 255, 255), 5)
            # Top-right
            cv2.line(img, (x + w, y), (x + w - corner_len, y), (0, 255, 255), 5)
            cv2.line(img, (x + w, y), (x + w, y + corner_len), (0, 255, 255), 5)
            # Bottom-left
            cv2.line(img, (x, y + h), (x + corner_len, y + h), (0, 255, 255), 5)
            cv2.line(img, (x, y + h), (x, y + h - corner_len), (0, 255, 255), 5)
            # Bottom-right
            cv2.line(img, (x + w, y + h), (x + w - corner_len, y + h), (0, 255, 255), 5)
            cv2.line(img, (x + w, y + h), (x + w, y + h - corner_len), (0, 255, 255), 5)

            # Label badge
            label = f"QR Code: {obj.get('location_desc', '')}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x, max(0, y - 28)), (x + lw + 10, max(0, y)), (255, 180, 0), -1)
            cv2.putText(img, label, (x + 5, max(18, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        return img


# Global singleton instance
_detector: VisualDetector | None = None

def get_visual_detector() -> VisualDetector:
    global _detector
    if _detector is None:
        _detector = VisualDetector()
    return _detector
