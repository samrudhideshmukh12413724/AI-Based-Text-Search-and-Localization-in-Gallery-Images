"""Steganography Reader & Document Authenticity Verification Module.

Provides:
1. Steganography Reader: Extracts hidden LSB (Least Significant Bit) text embedded inside image pixels.
2. Document Hash Verification: Generates SHA-256 tamper-evident cryptographic hashes for documents.
"""

import hashlib
from pathlib import Path
from typing import Union, Dict, Any, Optional
import cv2
import numpy as np


def compute_document_hash(image_input: Union[str, Path, np.ndarray]) -> str:
    """Computes SHA-256 cryptographic hash of image binary or pixel data."""
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    elif isinstance(image_input, np.ndarray):
        return hashlib.sha256(image_input.tobytes()).hexdigest()
    return ""


def extract_stego_text(image_input: Union[str, Path, np.ndarray]) -> str:
    """
    Extracts LSB (Least Significant Bit) hidden text payload from image pixels.
    Parses bit stream up to null terminator '\\x00'.
    """
    try:
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input

        if img is None:
            return ""

        # Flatten image pixels and extract LSB of blue/green/red channels
        flat_pixels = img.flatten()
        bits = [str(pixel & 1) for pixel in flat_pixels[:4096]]  # check first 4KB of bits
        bit_string = "".join(bits)

        # Convert bits to bytes
        bytes_list = []
        for i in range(0, len(bit_string) - 7, 8):
            byte = int(bit_string[i:i+8], 2)
            if byte == 0:  # null terminator
                break
            if 32 <= byte <= 126 or byte in (9, 10, 13):  # readable ASCII
                bytes_list.append(chr(byte))
            else:
                break

        extracted = "".join(bytes_list).strip()
        # Require minimum length and non-garbage pattern to avoid false positives on random noise
        if len(extracted) >= 4 and any(c.isalnum() for c in extracted):
            return extracted
        return ""
    except Exception:
        return ""


def verify_document_authenticity(image_path: str, expected_hash: str) -> Dict[str, Any]:
    """Verifies image hash against stored canonical hash to detect tampering."""
    current_hash = compute_document_hash(image_path)
    is_authentic = bool(current_hash and expected_hash and current_hash.lower() == expected_hash.lower())
    return {
        "is_authentic": is_authentic,
        "current_sha256": current_hash,
        "expected_sha256": expected_hash,
        "status": "AUTHENTIC" if is_authentic else "MODIFIED_OR_UNKNOWN"
    }
