"""Unit Tests for Change-Aware Retrieval (Idea 2) and Relevance Feedback Personalization (Idea 3).

Research Basis:
  Idea 2: Tracks visual transitions and state deltas across temporal photo sequences
          ('Find project photos before and after the motor was added').
  Idea 3: Implements Rocchio relevance feedback to adapt retrieval ranking to user intent
          ('classroom board' -> user rejects slides, selects whiteboards -> whiteboards rank higher).

Covers:
1. Multi-modal timeline grouping and chronological ordering.
2. Visual object set difference detection (added vs. removed items).
3. Operational status lifecycle transitions (UNPAID -> PAID, UNSIGNED -> SIGNED).
4. Change-aware query parsing and transition matching.
5. Rocchio relevance feedback vector recording.
6. Dynamic Paper 9 cross-weighted fusion adaptation based on user engagement.
7. Personalized re-ranking proving preferred modality overtakes rejected modality.
8. Single-tenant user feedback profile isolation.
"""

import pytest
from app.change_aware import ChangeAwareRetriever
from app.relevance_feedback import RelevanceFeedbackEngine


def test_change_aware_state_diffing():
    """
    Validates visual delta computation between sequential stages:
    Stage 1: chassis, breadboard
    Stage 2: chassis, breadboard, stepper_motor (motor added)
    """
    timeline = [
        {
            "id": 101,
            "image_name": "arduino_stage_1.jpg",
            "image_url": "/uploads/arduino_stage_1.jpg",
            "created_at": "2026-03-01T10:00:00",
            "category": "Robotics Project",
            "detected_objects": ["arduino", "breadboard", "chassis"],
            "status": "UNKNOWN",
            "text_preview": "arduino uno breadboard mounted on base chassis",
        },
        {
            "id": 102,
            "image_name": "arduino_stage_2.jpg",
            "image_url": "/uploads/arduino_stage_2.jpg",
            "created_at": "2026-03-01T14:30:00",
            "category": "Robotics Project",
            "detected_objects": ["arduino", "breadboard", "chassis", "motor", "stepper_motor"],
            "status": "UNKNOWN",
            "text_preview": "nema 17 stepper motor installed on chassis front",
        },
    ]

    transitions = ChangeAwareRetriever.compute_timeline_transitions(timeline)
    assert len(transitions) == 1
    t = transitions[0]

    assert t["stage_from"] == 1
    assert t["stage_to"] == 2
    assert "motor" in t["added_objects"]
    assert "stepper_motor" in t["added_objects"]
    assert len(t["removed_objects"]) == 0
    assert "Added motor, stepper_motor" in t["change_description"]


def test_change_aware_document_status_lifecycle():
    """
    Validates document lifecycle state change tracking:
    Bill Stage 1: UNPAID (Due Amount: 1420)
    Bill Stage 2: PAID (Transaction Successful)
    """
    timeline = [
        {
            "id": 201,
            "image_name": "msedcl_bill_unpaid.png",
            "image_url": "/uploads/msedcl_bill_unpaid.png",
            "created_at": "2026-02-10T09:00:00",
            "category": "Bills & Invoices",
            "detected_objects": ["bill", "meter"],
            "status": "UNPAID",
            "text_preview": "msedcl power bill due amount 1420 unpaid",
        },
        {
            "id": 202,
            "image_name": "msedcl_bill_receipt.png",
            "image_url": "/uploads/msedcl_bill_receipt.png",
            "created_at": "2026-02-11T16:00:00",
            "category": "Bills & Invoices",
            "detected_objects": ["bill", "receipt"],
            "status": "PAID",
            "text_preview": "payment cleared transaction successful paid",
        },
    ]

    transitions = ChangeAwareRetriever.compute_timeline_transitions(timeline)
    assert len(transitions) == 1
    t = transitions[0]

    assert t["status_transition"] == "UNPAID -> PAID"
    assert "receipt" in t["added_objects"]


def test_change_aware_query_resolution():
    """
    Tests end-to-end resolution of user change query:
    'Find project photos before and after the motor was added'
    """
    res = ChangeAwareRetriever.search_change_across_gallery("Find project photos before and after the motor was added")
    assert res["status"] == "success"
    assert res["target_change_entity"] == "motor"
    assert "total_timelines_analyzed" in res


def test_relevance_feedback_rocchio_learning_and_weight_adaptation():
    """
    Idea 3 Core: User feedback adapts ranking preferences and tunes Paper 9 fusion weights.
    """
    user_id = 999
    RelevanceFeedbackEngine.reset_profile(user_id)

    # User searches 'classroom board':
    # - Marks Doc 1 (physical classroom whiteboard) as RELEVANT
    # - Marks Doc 2 (powerpoint presentation slide) as IRRELEVANT
    feedback_result = RelevanceFeedbackEngine.record_feedback(
        user_id=user_id,
        query="classroom board",
        relevant_doc_ids=[1],
        irrelevant_doc_ids=[2],
    )

    assert feedback_result["status"] == "success"
    assert feedback_result["feedback_iterations"] == 1

    profile = RelevanceFeedbackEngine.get_user_profile(user_id)
    assert profile["feedback_iterations"] == 1
    assert "adapted_fusion_weights" in profile


def test_personalized_reranking_flips_ranking():
    """
    Validates that feedback learning successfully flips ranking order:
    Initially:
      - Candidate 1: Presentation Slide (relevance_score = 0.85)
      - Candidate 2: Classroom Whiteboard (relevance_score = 0.80)
    After user dislikes 'slide' and likes 'whiteboard':
      - Candidate 2 (Whiteboard) should jump to rank #1!
    """
    user_id = 888
    RelevanceFeedbackEngine.reset_profile(user_id)

    # Manually configure learned profile
    prof = RelevanceFeedbackEngine._user_profiles[user_id]
    prof["feedback_iterations"] = 2
    prof["positive_tags"]["whiteboard"] = 3.0
    prof["positive_tags"]["classroom"] = 2.0
    prof["negative_tags"]["slide"] = 4.0
    prof["negative_tags"]["presentation"] = 3.0

    raw_candidates = [
        {
            "id": 10,
            "image_name": "presentation_slide_deck.png",
            "text_preview": "presentation slide deck with bullet points",
            "relevance_score": 0.85,
        },
        {
            "id": 11,
            "image_name": "classroom_whiteboard_lecture.jpg",
            "text_preview": "classroom whiteboard notes written in marker",
            "relevance_score": 0.80,
        },
    ]

    reranked = RelevanceFeedbackEngine.apply_personalized_ranking(
        candidates=raw_candidates,
        user_id=user_id,
        query="classroom board",
    )

    # Whiteboard must now be #1
    assert reranked[0]["id"] == 11
    assert reranked[0]["personalized_score"] > reranked[1]["personalized_score"]
    assert reranked[0]["relevance_feedback_applied"] is True


def test_user_profile_isolation():
    """
    Validates that user A's feedback does not leak into user B's search profile.
    """
    RelevanceFeedbackEngine.reset_profile(1)
    RelevanceFeedbackEngine.reset_profile(2)

    prof1 = RelevanceFeedbackEngine._user_profiles[1]
    prof1["positive_tags"]["biology"] = 5.0
    prof1["feedback_iterations"] = 1

    prof2 = RelevanceFeedbackEngine.get_user_profile(2)
    assert prof2["feedback_iterations"] == 0
    assert prof2["status"] == "no_feedback_yet"
