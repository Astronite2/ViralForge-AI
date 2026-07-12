"""Platform content domain object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformContent:
    """Platform-neutral content representation."""

    platform: str
    external_id: str
    title: str
