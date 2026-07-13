"""AI reasoning exceptions."""

from __future__ import annotations


class ReasoningError(RuntimeError):
    """Base reasoning-layer error."""


class ReasoningDisabledError(ReasoningError):
    """Raised when the reasoning feature is unavailable."""


class ReasoningConfigurationError(ReasoningError):
    """Raised when reasoning is enabled but misconfigured."""


class ReasoningProviderError(ReasoningError):
    """Raised for provider-level failures."""


class ReasoningTransientProviderError(ReasoningProviderError):
    """Raised for retryable provider-level failures."""


class ReasoningValidationError(ReasoningError):
    """Raised when grounded output fails validation."""
