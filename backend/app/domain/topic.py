"""Topic domain object."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Topic:
    """A normalized human-readable topic."""

    id: str
    display_name: str
    normalized_key: str
    created_at: datetime
