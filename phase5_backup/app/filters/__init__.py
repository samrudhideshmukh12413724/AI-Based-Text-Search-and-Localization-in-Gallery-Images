"""Unified multi-faceted filtering subsystem for Phase 4 Step 8."""

from app.filters.models import FilterParams
from app.filters.candidate_filter import get_eligible_candidate_ids
from app.filters.date_filter import filter_by_date_range, filter_by_year
from app.filters.metadata_filter import filter_by_category, filter_by_format
from app.filters.entity_filter import filter_by_entity_type
from app.filters.visual_filter import filter_by_visual_type

__all__ = [
    "FilterParams",
    "get_eligible_candidate_ids",
    "filter_by_date_range",
    "filter_by_year",
    "filter_by_category",
    "filter_by_format",
    "filter_by_entity_type",
    "filter_by_visual_type",
]
