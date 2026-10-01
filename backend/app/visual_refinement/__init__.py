"""Modular CLIP Open-Vocabulary Search Refinement (Phase 4 Step 7A).

Provides explainable, deterministic visual search refinement over candidate visual regions
without object-specific classifiers or extra models.
"""

from app.visual_refinement.prompts import build_prompt_ensemble, sanitize_query
from app.visual_refinement.ranking import rank_visual_candidates
from app.visual_refinement.clip_refiner import (
    VisualRefiner,
    get_visual_refiner,
    DEFAULT_VISUAL_THRESHOLD,
)

__all__ = [
    "build_prompt_ensemble",
    "sanitize_query",
    "VisualRefiner",
    "get_visual_refiner",
    "rank_visual_candidates",
    "DEFAULT_VISUAL_THRESHOLD",
]
