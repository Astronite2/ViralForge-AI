"""Connector-level availability errors understood by orchestration."""

from __future__ import annotations


class ConnectorAvailabilityError(RuntimeError):
    """Expected connector state that should become a structured report."""

    report_status = "degraded"
    error_code = "connector_unavailable"

    def __init__(self, safe_message: str) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message


class ConnectorDisabledError(ConnectorAvailabilityError):
    """Connector was intentionally disabled by configuration."""

    report_status = "disabled"
    error_code = "disabled"


class ConnectorConfigurationRequiredError(ConnectorAvailabilityError):
    """Connector cannot run until required access is configured."""

    report_status = "unavailable"
    error_code = "configuration_required"


class ConnectorProviderUnavailableError(ConnectorAvailabilityError):
    """Configured provider is permanently unavailable for this request."""

    report_status = "unavailable"
    error_code = "provider_unavailable"


class ConnectorRateLimitError(ConnectorAvailabilityError):
    """Configured provider temporarily rejected requests due to rate limits."""

    report_status = "degraded"
    error_code = "rate_limited"


class ConnectorTransientError(ConnectorAvailabilityError):
    """Configured provider is temporarily unavailable."""

    report_status = "degraded"
    error_code = "temporary_failure"
