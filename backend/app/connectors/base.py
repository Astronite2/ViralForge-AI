"""Platform connector contract."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from backend.app.connectors.metadata import ConnectorCapabilities, ConnectorMetadata


class BaseConnector[TNormalized](ABC):
    """Interface implemented by external platform connectors."""

    @abstractmethod
    def fetch(self, **kwargs: Any) -> list[Mapping[str, Any]]:
        """Fetch raw payloads from a platform source."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_content: Mapping[str, Any]) -> TNormalized:
        """Convert platform data into a shared domain object."""
        raise NotImplementedError

    @abstractmethod
    def validate(self, raw_content: Mapping[str, Any]) -> None:
        """Validate the platform payload before pipeline processing."""
        raise NotImplementedError

    @property
    def metadata(self) -> ConnectorMetadata:
        """Return discoverable v2 metadata; subclasses should provide specifics."""
        name = self.__class__.__name__.removesuffix("Connector").lower()
        return ConnectorMetadata(
            name=name,
            display_name=name.replace("_", " ").title(),
            version="1.0.0",
            provider=name,
            description=self.__class__.__doc__ or "Platform connector",
            supports_live_access=self.is_enabled,
            supports_fixture_access=False,
        )

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return self.metadata.capabilities

    @property
    def is_enabled(self) -> bool:
        return True

    @property
    def availability(self) -> str:
        return "unobserved" if self.is_enabled else "disabled"

    def diagnostics(self) -> Mapping[str, Any]:
        """Return safe diagnostics without credentials or transport internals."""
        return {"availability": self.availability}
