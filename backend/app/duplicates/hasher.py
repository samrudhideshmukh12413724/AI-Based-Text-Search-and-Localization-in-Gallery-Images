"""Image Hashing Module for Exact and Near-Duplicate Detection.

Provides:
- compute_sha256: Bit-for-bit exact cryptographic checksum
- compute_phash: 64-bit Discrete Cosine Transform (DCT) perceptual hash
- hamming_distance: Bit difference count between two 64-bit hashes
- phash_similarity: Normalized hash similarity score [0.0, 1.0]
"""

import hashlib
from pathlib import Path
from typing import Union
import cv2
import numpy as np


def compute_sha256(image_path: Union[str, Path]) -> str:
    """
    Computes SHA-256 cryptographic checksum of raw image file bytes.
    Returns empty string if file does not exist or cannot be read.
    """
    path = Path(image_path)
    if not path.is_file():
        return ""

    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def compute_phash(
    image_path: Union[str, Path],
    hash_size: int = 8,
    highfreq_factor: int = 4,
) -> str:
    """
    Computes a 64-bit DCT perceptual hash (pHash) represented as a 16-char hex string.

    Steps:
    1. Read image safely via binary buffer and decode to grayscale.
    2. Resize to (hash_size * highfreq_factor) x (hash_size * highfreq_factor) (default 32x32).
    3. Compute 2D Discrete Cosine Transform (DCT).
    4. Extract the low-frequency 8x8 submatrix.
    5. Compute median of low-frequency AC coefficients (excluding DC at [0,0]).
    6. Generate 64 boolean bits (1 if coefficient > median else 0).
    7. Convert bits to 16-character hexadecimal string.

    Returns empty string if image cannot be read or is invalid.
    """
    path = Path(image_path)
    if not path.is_file():
        return ""

    try:
        with open(path, "rb") as f:
            data = f.read()
        if not data:
            return ""

        arr = np.frombuffer(data, dtype=np.uint8)
        gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if gray is None or gray.size == 0:
            return ""

        # Resize to 32x32
        dim = hash_size * highfreq_factor
        resized = cv2.resize(gray, (dim, dim), interpolation=cv2.INTER_AREA)

        # 2D Discrete Cosine Transform
        dct = cv2.dct(np.float32(resized))

        # Extract 8x8 low frequency region
        dct_low = dct[0:hash_size, 0:hash_size]

        # Compute median excluding the DC component at (0, 0)
        flat = dct_low.flatten()
        med = float(np.median(flat[1:]))

        # 64 bits: 1 if > median, else 0
        bits = (flat > med).astype(int)
        bit_str = "".join(str(b) for b in bits)

        # Format as 16-character hexadecimal string (64 bits = 16 hex digits)
        return f"{int(bit_str, 2):016x}"
    except Exception:
        return ""


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Computes the Hamming distance (number of differing bits) between two 16-char hex hashes.
    Returns 64 (maximum distance) if either hash is invalid or missing.
    """
    if not hash1 or not hash2 or len(hash1) != 16 or len(hash2) != 16:
        return 64

    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        return bin(xor_val).count("1")
    except ValueError:
        return 64


def phash_similarity(hash1: str, hash2: str) -> float:
    """
    Computes normalized hash-bit similarity in range [0.0, 1.0].
    similarity = 1.0 - (hamming_distance / 64)
    """
    dist = hamming_distance(hash1, hash2)
    return round(max(0.0, 1.0 - (dist / 64.0)), 4)
