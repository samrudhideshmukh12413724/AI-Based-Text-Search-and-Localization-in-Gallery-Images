"""PATENTABLE INNOVATION 3 (2026): Shannon Entropy-Weighted Adaptive Multi-Modal Fusion Ranker.

Calculates Shannon entropy H(Q) of search queries to dynamically adjust feature weights
across 6 modalities (OCR, Semantic Embeddings, BLIP Captions, QR Web Metadata, LSB Stego, and ELA Tampering).
"""

import math
from typing import Dict, Any


def compute_shannon_entropy(query: str) -> float:
    """Computes Shannon entropy H(Q) measuring query complexity and character distribution."""
    clean_q = query.strip().lower()
    if not clean_q:
        return 0.0

    length = len(clean_q)
    freq: Dict[str, int] = {}
    for c in clean_q:
        freq[c] = freq.get(c, 0) + 1

    entropy = 0.0
    for c, count in freq.items():
        p = count / length
        entropy -= p * math.log2(p)

    return round(entropy, 3)


class EntropyAdaptiveMultiModalRanker:
    """
    Patentable Ranker: Dynamically adjusts multi-modal weights based on Shannon Query Entropy H(Q).
    """

    def compute_adaptive_weights(self, query: str) -> Dict[str, float]:
        """
        Dynamically adjusts 6 modality weights based on query entropy H(Q).
        High entropy queries (complex phrase/sentences) -> Increase Semantic & BLIP weights.
        Low entropy queries (short keywords/IDs) -> Increase OCR & Exact QR weights.
        """
        entropy = compute_shannon_entropy(query)
        words = len(query.strip().split())

        if words <= 2 or entropy < 2.5:
            # Keyword / ID query mode
            w_ocr = 0.45
            w_semantic = 0.20
            w_blip = 0.10
            w_qr = 0.15
            w_stego = 0.05
            w_tamper_pen = 0.05
        else:
            # High-entropy natural language sentence mode
            w_ocr = 0.25
            w_semantic = 0.35
            w_blip = 0.25
            w_qr = 0.10
            w_stego = 0.03
            w_tamper_pen = 0.02

        return {
            "shannon_entropy": entropy,
            "w_ocr": w_ocr,
            "w_semantic": w_semantic,
            "w_blip": w_blip,
            "w_qr": w_qr,
            "w_stego": w_stego,
            "w_tamper_pen": w_tamper_pen,
        }

    def compute_entropy_fused_score(
        self,
        query: str,
        s_ocr: float,
        s_semantic: float,
        s_blip: float,
        s_qr: float,
        s_stego: float,
        tamper_score: float,
    ) -> float:
        """
        Computes final entropy-fused relevance score with dynamic tamper noise penalization.
        """
        w = self.compute_adaptive_weights(query)

        raw_score = (
            w["w_ocr"] * s_ocr
            + w["w_semantic"] * s_semantic
            + w["w_blip"] * s_blip
            + w["w_qr"] * s_qr
            + w["w_stego"] * s_stego
        )

        # Dynamic Tamper Noise Penalization
        tamper_penalty = w["w_tamper_pen"] * max(0.0, tamper_score - 0.50)
        final_score = max(0.0, min(1.0, raw_score - tamper_penalty))

        return round(final_score, 4)
