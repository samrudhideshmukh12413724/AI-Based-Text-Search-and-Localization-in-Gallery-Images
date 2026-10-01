"""Unified candidate eligibility filter coordinator for Phase 4 Step 8.

Integrates metadata, temporal, category, format, entity, and visual filters into
a single deterministic candidate pruning entry point.
"""

from typing import Set, Optional, List

from app import database
from app.filters.models import FilterParams
from app.filters.date_filter import filter_by_date_range, filter_by_year
from app.filters.metadata_filter import filter_by_category, filter_by_format
from app.filters.entity_filter import filter_by_entity_type
from app.filters.visual_filter import filter_by_visual_type


def get_eligible_candidate_ids(
    params: FilterParams,
    visual_refiner=None,
) -> Optional[Set[int]]:
    """
    Evaluates active structured filters and returns the set of eligible document IDs.

    Returns:
    - None : When NO filters are active (signals full unfiltered search path).
    - Set[int] : Eligible document IDs satisfying the strict logical AND intersection of all active filters.
                 If no documents satisfy all filters, returns an empty set set().
    """
    if not params.has_any_filter():
        return None

    # Load all indexed image metadata from database
    rows = database.list_images()
    if not rows:
        return set()

    active_filter_sets: List[Set[int]] = []

    # 1. Date Range Filter
    if bool(params.date_from and params.date_from.strip()) or bool(params.date_to and params.date_to.strip()):
        date_ids = filter_by_date_range(rows, date_from=params.date_from, date_to=params.date_to)
        active_filter_sets.append(date_ids)

    # 2. Year Filter
    if params.year is not None:
        year_ids = filter_by_year(rows, year=params.year)
        active_filter_sets.append(year_ids)

    # 3. Category Filter
    if bool(params.category and params.category.strip()):
        cat_ids = filter_by_category(rows, category=params.category)
        active_filter_sets.append(cat_ids)

    # 4. File Format Filter
    if bool(params.format and params.format.strip()):
        fmt_ids = filter_by_format(rows, file_format=params.format)
        active_filter_sets.append(fmt_ids)

    # 5. Entity Type Filter
    if bool(params.entity_type and params.entity_type.strip()):
        ent_ids = filter_by_entity_type(rows, entity_type=params.entity_type)
        active_filter_sets.append(ent_ids)

    # 6. Visual Type Filter
    if bool(params.visual_type and params.visual_type.strip()):
        vis_ids = filter_by_visual_type(rows, visual_type=params.visual_type, visual_refiner=visual_refiner)
        active_filter_sets.append(vis_ids)

    if not active_filter_sets:
        return None

    # Strict logical AND intersection of all active filters
    eligible_ids = set.intersection(*active_filter_sets)
    return eligible_ids
