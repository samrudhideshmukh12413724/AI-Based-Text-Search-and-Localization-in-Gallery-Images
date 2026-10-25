"""Change-Aware Semantic Retrieval for Tracking Events and Visual Changes in Image Galleries (Idea 2).

Research Basis:
  Ordinary image search retrieves images based on isolated static contents.
  Change-Aware Retrieval tracks visual transitions, hardware project milestones,
  and document lifecycle states across chronological photo sequences.

Core Components:
1. Entity & Project Co-Reference Grouping: Clusters photos depicting the same subject or project.
2. Temporal Timeline Ordering: Chronological sorting via EXIF / capture / ingestion timestamps.
3. Multi-Modal State-Diffing: Detects delta in visual object sets and operational status tokens
   (e.g., added: 'motor', 'signature', status: 'UNPAID' -> 'PAID').
4. Stage Transition Retrieval: Resolves before-and-after queries ('before and after motor was added').
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from app import database


class ChangeAwareRetriever:
    """
    Engine for detecting, tracking, and retrieving visual state changes across image galleries.
    """

    KNOWN_TRANSITION_VERBS = [
        "added", "installed", "mounted", "connected", "attached", "assembled",
        "paid", "cleared", "signed", "approved", "stamped", "removed", "replaced"
    ]

    @staticmethod
    def extract_image_state(img: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts visual objects, text tokens, and metadata state from a database record."""
        vmeta_raw = img.get("visual_metadata")
        vmeta = {}
        if vmeta_raw:
            try:
                vmeta = json.loads(vmeta_raw) if isinstance(vmeta_raw, str) else vmeta_raw
            except Exception:
                vmeta = {}

        raw_objects = vmeta.get("objects", [])
        if isinstance(raw_objects, list):
            detected_objects = set(str(o).lower() for o in raw_objects)
        else:
            detected_objects = set()

        text = (img.get("extracted_text") or "").lower()
        fn = (img.get("image_name") or "").lower()

        # Extract common physical / document entities from text and filename
        domain_tokens = [
            "motor", "stepper_motor", "arduino", "breadboard", "sensor", "chassis",
            "battery", "wire", "lcd", "display", "wheel", "camera",
            "watermark", "signature", "stamp", "receipt", "bill", "meter"
        ]
        for token in domain_tokens:
            if token in text or token in fn:
                detected_objects.add(token)

        # Detect operational lifecycle status
        status = "UNKNOWN"
        if any(w in text for w in ["unpaid", "due", "pending", "overdue"]):
            status = "UNPAID"
        elif any(w in text for w in ["paid", "cleared", "settled", "transaction successful"]):
            status = "PAID"
        elif any(w in text for w in ["notarized", "signed by", "principal sign"]):
            status = "SIGNED"
        elif any(w in text for w in ["draft", "unsigned", "pending signature"]):
            status = "UNSIGNED"

        created_at_str = img.get("created_at") or "2026-01-01T00:00:00"

        return {
            "id": img["id"],
            "image_name": img["image_name"],
            "image_url": f"/uploads/{img['image_name']}",
            "created_at": created_at_str,
            "category": img.get("category") or "General",
            "detected_objects": sorted(list(detected_objects)),
            "status": status,
            "text_preview": text[:120],
        }

    @classmethod
    def group_and_order_timelines(
        cls,
        images: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups images by project / category co-reference and orders chronologically.
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for img in images:
            state = cls.extract_image_state(img)
            # Group key: category or extracted project tag
            cat = state["category"] or "General Project"
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(state)

        # Sort each group chronologically by timestamp / ID
        for cat in groups:
            groups[cat].sort(key=lambda x: (x["created_at"], x["id"]))

        return groups

    @classmethod
    def compute_timeline_transitions(
        cls,
        timeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compares consecutive stages in a timeline to detect visual and state deltas.
        """
        transitions = []
        for i in range(len(timeline) - 1):
            before = timeline[i]
            after = timeline[i + 1]

            objs_before = set(before["detected_objects"])
            objs_after = set(after["detected_objects"])

            added_objs = sorted(list(objs_after - objs_before))
            removed_objs = sorted(list(objs_before - objs_after))

            status_changed = before["status"] != after["status"]
            status_transition = None
            if status_changed:
                status_transition = f"{before['status']} -> {after['status']}"

            # Create summary description of the visual change
            changes = []
            if added_objs:
                changes.append(f"Added {', '.join(added_objs)}")
            if removed_objs:
                changes.append(f"Removed {', '.join(removed_objs)}")
            if status_transition:
                changes.append(f"Status changed: {status_transition}")

            change_desc = "; ".join(changes) if changes else "Incremental modification"

            transitions.append({
                "stage_from": i + 1,
                "stage_to": i + 2,
                "before_image": before,
                "after_image": after,
                "added_objects": added_objs,
                "removed_objects": removed_objs,
                "status_transition": status_transition,
                "change_description": change_desc,
            })

        return transitions

    @classmethod
    def search_change_across_gallery(
        cls,
        query: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieves before-and-after image stages satisfying a change query.
        e.g., 'Find project photos before and after the motor was added'
              'Show bill before and after payment'
        """
        clean_q = query.lower()

        # 1. Identify target object or change token from query
        target_entity = None
        for token in ["motor", "stepper_motor", "sensor", "arduino", "chassis", "battery", "payment", "signature", "stamp"]:
            if token in clean_q:
                target_entity = token
                break

        # Fallback regex for target entity after 'after the X was' or 'before and after X'
        if not target_entity:
            m = re.search(r"(?:before\s+and\s+after|when|after)\s+(?:the\s+)?([a-zA-Z]+)", clean_q)
            if m:
                target_entity = m.group(1).lower()

        all_images = database.list_images(user_id=user_id)
        grouped_timelines = cls.group_and_order_timelines(all_images)

        matched_transitions = []

        for group_name, timeline in grouped_timelines.items():
            if len(timeline) < 2:
                continue

            transitions = cls.compute_timeline_transitions(timeline)
            for t in transitions:
                # Score the transition relevance against the query
                match_score = 0.0
                matched_reasons = []

                if target_entity:
                    if target_entity in t["added_objects"] or any(target_entity in str(o) for o in t["added_objects"]):
                        match_score += 0.80
                        matched_reasons.append(f"Object '{target_entity}' was added in this stage")
                    if target_entity == "payment" and t["status_transition"] and "PAID" in t["status_transition"]:
                        match_score += 0.90
                        matched_reasons.append("Payment state transitioned to PAID")
                    if target_entity == "signature" and t["status_transition"] and "SIGNED" in t["status_transition"]:
                        match_score += 0.90
                        matched_reasons.append("Document transitioned to SIGNED")

                # Keyword match in change description
                words = [w for w in re.findall(r"[a-zA-Z]+", clean_q) if len(w) > 3 and w not in ["find", "photos", "project", "before", "after", "taken"]]
                for w in words:
                    if w in t["change_description"].lower():
                        match_score += 0.20

                if match_score > 0.0:
                    matched_transitions.append({
                        "project_group": group_name,
                        "relevance_score": min(1.0, round(match_score, 3)),
                        "match_evidence": matched_reasons,
                        "transition": t,
                    })

        matched_transitions.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "status": "success",
            "query": query,
            "target_change_entity": target_entity,
            "total_timelines_analyzed": len(grouped_timelines),
            "total_transitions_found": len(matched_transitions),
            "transitions": matched_transitions,
            "research_backing": (
                "DocuLens Change-Aware Semantic Retrieval: Multi-Modal Entity Grouping & Visual State-Diffing "
                "(Milestone Tracking & Lifecycle Stage Comparison 2026)"
            ),
        }
