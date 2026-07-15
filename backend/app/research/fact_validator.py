"""Deterministic citation integrity checks."""

from enum import StrEnum


class VerificationStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


def validate_fact(
    fact: dict[str, object], source_ids: set[str]
) -> dict[str, object] | None:
    """Reject ungrounded claims and citations that do not exist."""
    references = fact.get("supporting_source_ids")
    if not isinstance(references, list) or not references:
        return None
    if any(reference not in source_ids for reference in references):
        return None
    status = str(fact.get("verification_status", "UNVERIFIED"))
    if status == VerificationStatus.UNVERIFIED.value:
        return None
    if status not in {item.value for item in VerificationStatus}:
        return None
    return fact
