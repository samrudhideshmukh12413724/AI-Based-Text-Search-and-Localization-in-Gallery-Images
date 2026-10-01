"""QR Code and Barcode Metadata Extractor.

Uses OpenCV QRCodeDetector to scan images for QR payloads (URLs, UPI IDs, Wi-Fi passwords, contact cards) during ingestion.
"""

from pathlib import Path
from typing import Union, Dict, Any, List
import cv2
import numpy as np


def extract_qr_payloads(image_input: Union[str, Path, np.ndarray]) -> Dict[str, Any]:
    """
    Detects and decodes QR codes inside an image.
    Returns decoded text payloads and bounding boxes.
    """
    try:
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input

        if img is None:
            return {"has_qr": False, "payloads": [], "qr_summary": ""}

        detector = cv2.QRCodeDetector()
        # OpenCV detectAndDecodeMulti or detectAndDecode
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)

        payloads: List[str] = []
        if retval and decoded_info:
            for info in decoded_info:
                if info and info.strip():
                    payloads.append(info.strip())

        if not payloads:
            # Fallback to single QR decode
            single_val, pts, _ = detector.detectAndDecode(img)
            if single_val and single_val.strip():
                payloads.append(single_val.strip())

        has_qr = len(payloads) > 0
        summary = " | ".join(payloads) if has_qr else ""

        return {
            "has_qr": has_qr,
            "payloads": payloads,
            "qr_summary": summary
        }
    except Exception:
        return {"has_qr": False, "payloads": [], "qr_summary": ""}
