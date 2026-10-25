"""Personalized Text-to-Image Retrieval Using Relevance Feedback and Adaptive Ranking (Idea 3).

Research Basis:
  Overcomes the static ranking limitation where two users with identical search terms
  have divergent intents (e.g., 'classroom board' -> user selects physical whiteboards, rejects presentation slides).
  Implements Rocchio-inspired Relevance Feedback and Adaptive Margin Re-weighting
  to personalize subsequent retrievals within a user's private gallery.

Key Components:
1. Multi-Turn Relevance Feedback (Relevant / Irrelevant signals per document).
2. Rocchio-Inspired Feature Shifting (Positive boost vs. Negative suppression).
3. Dynamic Preference Profiling per user.
4. Personalized Re-Ranking Engine preserving single-tenant data isolation.
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional
from app import database


class RelevanceFeedbackEngine:
    """
    Manages user-specific relevance feedback, tag preference vectors,
    and adaptive re-ranking for personalized retrieval.
    """

    # In-memory user preference cache (keyed by user_id)
    _user_profiles: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "positive_tags": defaultdict(float),
        "negative_tags": defaultdict(float),
        "preferred_categories": defaultdict(float),
        "rejected_categories": defaultdict(float),
        "feedback_iterations": 0,
        "alpha_text_weight": 0.40,
        "beta_visual_weight": 0.40,
        "gamma_proximity_weight": 0.20,
    })

    @classmethod
    def record_feedback(
        cls,
        user_id: int,
        query: str,
        relevant_doc_ids: List[int],
        irrelevant_doc_ids: List[int],
    ) -> Dict[str, Any]:
        """
        Processes multi-turn relevance feedback from the user.
        Boosts positive visual attributes and penalizes rejected traits.
        """
        profile = cls._user_profiles[user_id]
        profile["feedback_iterations"] += 1

        all_images = {img["id"]: img for img in database.list_images(user_id=user_id)}

        # 1. Process Positive / Relevant Feedback (Rocchio beta reinforcement)
        for doc_id in relevant_doc_ids:
            img = all_images.get(doc_id)
            if not img:
                continue

            cat = img.get("category")
            if cat:
                profile["preferred_categories"][cat] += 1.0

            text_words = (img.get("extracted_text") or "").lower().split()
            for w in set(text_words):
                if len(w) > 3:
                    profile["positive_tags"][w] += 0.50

            # Visual metadata tags
            vmeta = cls._parse_vmeta(img)
            for obj in vmeta.get("objects", []):
                profile["positive_tags"][str(obj).lower()] += 1.0

        # 2. Process Negative / Irrelevant Feedback (Rocchio gamma suppression)
        for doc_id in irrelevant_doc_ids:
            img = all_images.get(doc_id)
            if not img:
                continue

            cat = img.get("category")
            if cat:
                profile["rejected_categories"][cat] += 1.0

            text_words = (img.get("extracted_text") or "").lower().split()
            for w in set(text_words):
                if len(w) > 3:
                    profile["negative_tags"][w] += 0.50

            # Visual metadata tags
            vmeta = cls._parse_vmeta(img)
            for obj in vmeta.get("objects", []):
                profile["negative_tags"][str(obj).lower()] += 1.0

        # Dynamically adapt Paper 9 fusion weights:
        # If user frequently selects visual objects over text, increase visual weight
        pos_vis_count = sum(profile["positive_tags"].values())
        if pos_vis_count > 5.0:
            profile["beta_visual_weight"] = 0.55
            profile["alpha_text_weight"] = 0.30
            profile["gamma_proximity_weight"] = 0.15

        return {
            "status": "success",
            "user_id": user_id,
            "feedback_iterations": profile["feedback_iterations"],
            "top_preferred_tags": sorted(profile["positive_tags"].items(), key=lambda x: x[1], reverse=True)[:5],
            "top_rejected_tags": sorted(profile["negative_tags"].items(), key=lambda x: x[1], reverse=True)[:5],
            "adapted_fusion_weights": {
                "alpha": profile["alpha_text_weight"],
                "beta": profile["beta_visual_weight"],
                "gamma": profile["gamma_proximity_weight"],
            },
        }

    @classmethod
    def apply_personalized_ranking(
        cls,
        candidates: List[Dict[str, Any]],
        user_id: int,
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Re-ranks search candidates using learned user relevance preferences.
        Boosts images with high positive affinity, penalizes images matching rejected tags.
        """
        profile = cls._user_profiles.get(user_id)
        if not profile or profile["feedback_iterations"] == 0:
            return candidates

        pos_tags = profile["positive_tags"]
        neg_tags = profile["negative_tags"]

        reranked = []
        for cand in candidates:
            base_score = cand.get("relevance_score", 0.50)
            text_lower = (cand.get("text_preview") or "").lower()
            name_lower = (cand.get("image_name") or "").lower()

            # Positive boost
            pos_matches = sum(weight for tag, weight in pos_tags.items() if tag in text_lower or tag in name_lower)
            pos_boost = min(0.40, 0.08 * pos_matches)

            # Negative penalty
            neg_matches = sum(weight for tag, weight in neg_tags.items() if tag in text_lower or tag in name_lower)
            neg_penalty = min(0.60, 0.15 * neg_matches)

            personalized_score = max(0.01, round(base_score + pos_boost - neg_penalty, 3))

            cand_copy = dict(cand)
            cand_copy["base_score"] = base_score
            cand_copy["personalized_score"] = personalized_score
            cand_copy["relevance_score"] = personalized_score
            cand_copy["relevance_feedback_applied"] = True
            reranked.append(cand_copy)

        reranked.sort(key=lambda x: x["personalized_score"], reverse=True)
        return reranked

    @classmethod
    def get_user_profile(cls, user_id: int) -> Dict[str, Any]:
        """Returns the current personalized feedback profile for the user."""
        profile = cls._user_profiles.get(user_id)
        if not profile:
            return {"user_id": user_id, "feedback_iterations": 0, "status": "no_feedback_yet"}

        return {
            "user_id": user_id,
            "feedback_iterations": profile["feedback_iterations"],
            "top_preferred_tags": sorted(profile["positive_tags"].items(), key=lambda x: x[1], reverse=True)[:10],
            "top_rejected_tags": sorted(profile["negative_tags"].items(), key=lambda x: x[1], reverse=True)[:10],
            "adapted_fusion_weights": {
                "alpha": profile["alpha_text_weight"],
                "beta": profile["beta_visual_weight"],
                "gamma": profile["gamma_proximity_weight"],
            },
        }

    @classmethod
    def reset_profile(cls, user_id: int) -> None:
        """Resets the personalized feedback profile for a given user."""
        if user_id in cls._user_profiles:
            del cls._user_profiles[user_id]

    @staticmethod
    def _parse_vmeta(img: Dict[str, Any]) -> Dict[str, Any]:
        vmeta_raw = img.get("visual_metadata")
        if not vmeta_raw:
            return {}
        try:
            return json.loads(vmeta_raw) if isinstance(vmeta_raw, str) else vmeta_raw
        except Exception:
            return {}
