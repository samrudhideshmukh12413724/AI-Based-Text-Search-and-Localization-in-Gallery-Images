"""Filter parameter models for Phase 4 Step 8: Unified Multi-Faceted Filtered Search."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterParams:
    """Structured optional filters supported by the unified search engine."""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    format: Optional[str] = None
    visual_type: Optional[str] = None
    entity_type: Optional[str] = None

    def has_any_filter(self) -> bool:
        """Returns True if at least one filter criterion is active."""
        return any([
            bool(self.date_from and self.date_from.strip()),
            bool(self.date_to and self.date_to.strip()),
            self.year is not None,
            bool(self.category and self.category.strip()),
            bool(self.format and self.format.strip()),
            bool(self.visual_type and self.visual_type.strip()),
            bool(self.entity_type and self.entity_type.strip()),
        ])
