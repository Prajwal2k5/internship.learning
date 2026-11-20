
from pydantic import BaseModel, Field


class SnapshotIdentityMatch(BaseModel):
    """
    Represents one AML identity matched across the
    Standard Source, Customer Source and Standard Target.
    """

    customer_id: str
    identity_key: str

    item_type: str | None = None
    item_id: str | None = None

    standard_source: list[dict] = Field(default_factory=list)
    customer_source: list[dict] = Field(default_factory=list)
    standard_target: list[dict] = Field(default_factory=list)

    classification: str

    has_repeated_occurrences: bool = False


class SnapshotMatchingReport(BaseModel):
    """
    Complete identity matching report for all customers.
    """

    matches: list[SnapshotIdentityMatch] = Field(
        default_factory=list
    )

    total_matched_identities: int = 0

    query_records_excluded: int = 0

    missing_identity_records_excluded: int = 0

    repeated_identity_groups: int = 0

    classification_summary: dict[str, int] = Field(
        default_factory=dict
    )
