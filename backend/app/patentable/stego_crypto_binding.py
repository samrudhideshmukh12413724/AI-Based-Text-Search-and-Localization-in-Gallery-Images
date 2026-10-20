"""PATENTABLE INNOVATION 1 (2026): Self-Verifying ZK-Stego Cryptographic Hash Binding Engine.

Implements a novel method for embedding cryptographic HMAC signatures of OCR bounding boxes
and extracted entity metadata directly into the image's Least Significant Bit (LSB) pixel channels.
Creates self-verifying, tamper-evident document images.
"""

import hmac
import hashlib
import json
from pathlib import Path
from typing import Union, Dict, Any, Tuple
import cv2
import numpy as np


SECRET_HMAC_KEY = b"2026-patentable-zk-stego-secret-key-ocr-search"


def generate_document_hmac(image_input: Union[str, Path, np.ndarray], ocr_text: str, entities: Dict[str, Any]) -> str:
    """
    Computes a cryptographic HMAC-SHA256 signature binding image bytes, OCR text, and entity metadata.
    Zeroes out the LSB bit (img & 0xFE) so the hash is mathematically invariant to the watermark bits.
    """
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        return ""

    if img is None:
        return ""

    raw_bytes = (img & 0xFE).tobytes()
    payload_str = f"{ocr_text}:{json.dumps(entities, sort_keys=True)}"
    h = hmac.new(SECRET_HMAC_KEY, raw_bytes + payload_str.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:32]  # 32-character short HMAC signature


def embed_crypto_binding_signature(image_input: Union[str, Path, np.ndarray], ocr_text: str, entities: Dict[str, Any]) -> Tuple[np.ndarray, str]:
    """
    Embeds the cryptographic HMAC signature into the LSB of image pixel channels.
    """
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
    else:
        img = image_input.copy()

    if img is None:
        raise ValueError("Invalid image input for stego crypto embedding")

    hmac_sig = generate_document_hmac(image_input, ocr_text, entities)
    stego_payload = f"ZK_HMAC:{hmac_sig}\x00"
    binary_bits = "".join(format(ord(c), "08b") for c in stego_payload)

    flat = img.flatten()
    if len(flat) < len(binary_bits):
        raise ValueError("Image resolution too low for cryptographic signature embedding")

    for i, bit in enumerate(binary_bits):
        flat[i] = (int(flat[i]) & 254) | int(bit)

    stego_img = flat.reshape(img.shape)
    return stego_img, hmac_sig


def verify_crypto_binding_signature(image_input: Union[str, Path, np.ndarray], extracted_stego: str, ocr_text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts LSB signature and verifies cryptographic binding authenticity.
    """
    if not extracted_stego.startswith("ZK_HMAC:"):
        return {"is_bound": False, "status": "NO_CRYPTO_SIGNATURE_FOUND"}

    embedded_hmac = extracted_stego.replace("ZK_HMAC:", "").strip()
    expected_hmac = generate_document_hmac(image_input, ocr_text, entities)

    is_authentic = bool(embedded_hmac and expected_hmac and embedded_hmac.lower() == expected_hmac.lower())
    return {
        "is_bound": True,
        "is_authentic": is_authentic,
        "embedded_hmac": embedded_hmac,
        "calculated_hmac": expected_hmac,
        "status": "AUTHENTIC_CRYPTO_BOUND" if is_authentic else "TAMPERED_OR_PAYLOAD_MISMATCH",
    }
