
from pydantic import BaseModel, Field


class SemanticChangeRecord(BaseModel):
    """Semantic comparison result for one AML identity."""

    customer_id: str
    identity_key: str

    item_type: str | None = None
    item_id: str | None = None

    classification: str
    presence_classification: str = "present_in_all"

    # Changes relative to Standard Source.
    customer_changed_fields: list[str] = Field(
        default_factory=list
    )
    vendor_changed_fields: list[str] = Field(
        default_factory=list
    )

    # Same field changed differently by both sides.
    conflicting_fields: list[str] = Field(
        default_factory=list
    )

    # Same field changed to the same final value.
    convergent_fields: list[str] = Field(
        default_factory=list
    )

    # Structures that need manual review.
    ambiguous_structure_paths: list[str] = Field(
        default_factory=list
    )

    # Canonical payloads retained for audit and explanation.
    standard_source_payload: dict | None = None
    customer_source_payload: dict | None = None
    standard_target_payload: dict | None = None

    # Occurrence counts across snapshots.
    standard_source_occurrences: int = 0
    customer_source_occurrences: int = 0
    standard_target_occurrences: int = 0


class SemanticComparisonReport(BaseModel):
    """Complete semantic comparison report for all customers."""

    records: list[SemanticChangeRecord] = Field(
        default_factory=list
    )

    total_identities: int = 0
    compared_identities: int = 0

    skipped_repeated_identities: int = 0
    skipped_non_common_identities: int = 0
    skipped_ambiguous_structures: int = 0

    query_records_excluded: int = 0
    missing_identity_records_excluded: int = 0

    classification_summary: dict[str, int] = Field(
        default_factory=dict
    )
