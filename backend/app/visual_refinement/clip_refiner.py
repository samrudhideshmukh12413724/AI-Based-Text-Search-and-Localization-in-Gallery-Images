"""CLIP Open-Vocabulary Visual Refiner Module for Phase 4 Step 7A.

Reuses the existing CLIP model and visual-region database infrastructure to perform
deterministic prompt ensembling and open-vocabulary region scoring without separate classifiers.
"""

from collections import OrderedDict
from typing import List, Dict, Tuple, Any, Optional
import numpy as np
import torch

from app import database
from app.visual_refinement.prompts import build_prompt_ensemble, sanitize_query
from app.visual_refinement.ranking import rank_visual_candidates

DEFAULT_VISUAL_THRESHOLD: float = 0.245
DEFAULT_CACHE_MAX_SIZE: int = 256


class VisualRefiner:
    """
    Modular Open-Vocabulary Visual Refiner with LRU Query Embedding Cache (Phase 4 Step 7B).
    Reuses the existing VisualSearchEngine's CLIP ViT-B/32 instance and visual regions database.
    """

    def __init__(self, visual_engine=None, cache_max_size: int = DEFAULT_CACHE_MAX_SIZE):
        if visual_engine is None:
            from app.visual_search import get_visual_search_engine
            visual_engine = get_visual_search_engine()

        self.engine = visual_engine
        self.model = visual_engine.model
        self.tokenizer = visual_engine.tokenizer
        self.device = visual_engine.device

        # Step 7B: LRU Query Embedding Cache
        self.cache_max_size: int = cache_max_size
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self.cache_hits: int = 0
        self.cache_misses: int = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns lightweight cache metrics for diagnostics and benchmarking."""
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "size": len(self._cache),
            "max_size": self.cache_max_size,
        }

    def clear_cache(self) -> None:
        """Clears all cached query embeddings and resets hit/miss counters."""
        self._cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def encode_query(self, query: str, bypass_cache: bool = False) -> np.ndarray:
        """
        Accepts a natural-language query, generates a generic prompt ensemble,
        obtains CLIP text embeddings, normalizes them, aggregates them, and returns
        a final normalized 512-dim vector.

        Step 7B Optimization:
        - Uses deterministic sanitized query string as cache key.
        - Cache hit skips CLIP text encoding entirely.
        - Cache miss tokenizes and encodes the ensemble in a single batch.
        - Bounded LRU eviction preserves bounded memory usage.
        """
        clean_q = sanitize_query(query)
        if not clean_q:
            return np.zeros((1, 512), dtype=np.float32)

        # 1. Cache lookup
        if not bypass_cache and clean_q in self._cache:
            self.cache_hits += 1
            self._cache.move_to_end(clean_q)
            return self._cache[clean_q].copy()

        if not bypass_cache:
            self.cache_misses += 1

        # 2. Build deterministic prompt ensemble
        prompts = build_prompt_ensemble(clean_q)
        if not prompts:
            return np.zeros((1, 512), dtype=np.float32)

        # 3. Batch tokenize all prompts together in one batch
        text_inputs = self.tokenizer(prompts, padding=True, return_tensors="pt").to(self.device)

        # 4. Single model forward pass
        with torch.no_grad():
            text_features = self.model.get_text_features(**text_inputs)
            # Step 4: Normalize every prompt embedding independently
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            # Step 5: Average normalized embeddings deterministically
            ensemble_vec = text_features.mean(dim=0, keepdim=True)
            # Step 6: Normalize final aggregate embedding
            ensemble_vec = ensemble_vec / ensemble_vec.norm(p=2, dim=-1, keepdim=True)

        vec_np = ensemble_vec.cpu().numpy().astype(np.float32)

        # 5. Store in LRU cache
        if not bypass_cache:
            if len(self._cache) >= self.cache_max_size:
                self._cache.popitem(last=False)  # Evict least recently used
            self._cache[clean_q] = vec_np.copy()

        return vec_np.copy()

    def score_candidate_regions(
        self,
        query_vec: np.ndarray,
        regions: List[Dict[str, Any]],
        threshold: float = DEFAULT_VISUAL_THRESHOLD,
    ) -> Dict[int, List[Tuple[float, Dict[str, Any]]]]:
        """
        Computes cosine similarity between normalized query vector and stored visual regions.
        Filters candidate patches meeting the calibrated operational threshold.
        """
        doc_patches: Dict[int, List[Tuple[float, Dict[str, Any]]]] = {}

        for r in regions:
            emb_blob = r.get("embedding_blob")
            if not emb_blob:
                continue

            try:
                vec = np.frombuffer(emb_blob, dtype=np.float32).reshape(1, 512)
            except Exception:
                continue

            sim = float(np.dot(query_vec, vec.T)[0, 0])
            img_id = r.get("image_id")

            if img_id is not None and sim >= threshold:
                if img_id not in doc_patches:
                    doc_patches[img_id] = []
                doc_patches[img_id].append((sim, r))

        return doc_patches

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = DEFAULT_VISUAL_THRESHOLD,
        bypass_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Executes modular, open-vocabulary refined visual search across all indexed regions.
        """
        all_regions = database.get_all_visual_regions()
        if not all_regions:
            return []

        query_vec = self.encode_query(query, bypass_cache=bypass_cache)
        doc_patches = self.score_candidate_regions(query_vec, all_regions, threshold=threshold)
        return rank_visual_candidates(doc_patches, top_k=top_k, query=query)


_refiner_instance: Optional[VisualRefiner] = None


def get_visual_refiner(visual_engine=None) -> VisualRefiner:
    """Returns the shared VisualRefiner singleton, ensuring zero redundant models in memory."""
    global _refiner_instance
    if _refiner_instance is None:
        _refiner_instance = VisualRefiner(visual_engine)
    return _refiner_instance
