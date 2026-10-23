"""Phase 5 Custom Hybrid Multi-Modal Scoring & Adaptive Dynamic Thresholding Engine.

This module implements the custom mathematical formulation that unifies 6 search signals:
1. OCR Text Lexical Score (BM25 / Edit Distance)
2. Semantic Vector Score (Sentence-Transformers / FAISS Cosine Similarity)
3. BLIP Image Caption Similarity Score
4. QR Code & Barcode Payload Exact Match
5. YOLOv8 Visual Object Detection & Bounding Box Confidence Score
6. Steganography Hidden Text Payload Score

Also provides Adaptive Dynamic Thresholding tau_adaptive(Q, scores) to replace fixed cutoffs.
"""

import math
from typing import Dict, List, Any


class CustomHybridScorer:
    def __init__(
        self,
        w_ocr: float = 0.35,
        w_semantic: float = 0.25,
        w_blip: float = 0.15,
        w_qr: float = 0.10,
        w_visual: float = 0.10,
        w_stego: float = 0.05,
        tau_min: float = 0.30,
        k_sigma: float = 0.20,
        alpha_len: float = 0.05,
    ):
        # Normalize weights to sum to 1.0
        total_w = w_ocr + w_semantic + w_blip + w_qr + w_visual + w_stego
        self.w_ocr = w_ocr / total_w
        self.w_semantic = w_semantic / total_w
        self.w_blip = w_blip / total_w
        self.w_qr = w_qr / total_w
        self.w_visual = w_visual / total_w
        self.w_stego = w_stego / total_w

        self.tau_min = tau_min
        self.k_sigma = k_sigma
        self.alpha_len = alpha_len

    def compute_hybrid_score(
        self,
        s_ocr: float = 0.0,
        s_semantic: float = 0.0,
        s_blip: float = 0.0,
        s_qr: float = 0.0,
        s_visual: float = 0.0,
        s_stego: float = 0.0,
    ) -> float:
        """Compute weighted hybrid score S_hybrid in range [0.0, 1.0]."""
        score = (
            self.w_ocr * max(0.0, min(1.0, s_ocr))
            + self.w_semantic * max(0.0, min(1.0, s_semantic))
            + self.w_blip * max(0.0, min(1.0, s_blip))
            + self.w_qr * max(0.0, min(1.0, s_qr))
            + self.w_visual * max(0.0, min(1.0, s_visual))
            + self.w_stego * max(0.0, min(1.0, s_stego))
        )
        return round(float(score), 4)

    def compute_adaptive_threshold(self, query: str, scores: List[float]) -> float:
        """Compute query-length and variance dependent dynamic threshold tau_adaptive.

        Formula:
          tau_adaptive = max(tau_min, mu_scores + k_sigma * sigma_scores - alpha_len * log(1 + len(Q)))
        """
        if not scores:
            return self.tau_min

        n = len(scores)
        mu = sum(scores) / n
        variance = sum((s - mu) ** 2 for s in scores) / n
        sigma = math.sqrt(variance)

        q_len = len(query.strip())
        len_penalty = self.alpha_len * math.log(1 + q_len)

        raw_tau = mu + self.k_sigma * sigma - len_penalty
        adaptive_tau = max(self.tau_min, min(0.85, raw_tau))
        return round(float(adaptive_tau), 4)


_global_scorer = CustomHybridScorer()


def get_custom_scorer() -> CustomHybridScorer:
    return _global_scorer
