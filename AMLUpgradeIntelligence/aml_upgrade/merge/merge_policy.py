from __future__ import annotations

from typing import Any


REVIEW_CLASSIFICATIONS = {
    "ambiguous_repeated_identity",
    "ambiguous_structure_requires_review",
    "presence_requires_review",
}

CONFLICT_CLASSIFICATIONS = {"conflict"}


def identity_from_payload(value: Any) -> str | None:
    """Return Type:ID for a normalized AML Item payload."""
    if not isinstance(value, dict):
        return None

    item_type = value.get("item_type")
    item_id = value.get("item_id")

    if item_type and item_id:
        return f"{item_type}:{item_id}"

    return None


def is_aml_item_payload(value: Any) -> bool:
    return identity_from_payload(value) is not None


def get_value_at_path(payload: Any, path: str) -> Any:
    """Read a dotted path; intended for diagnostics and tests."""
    current = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current
