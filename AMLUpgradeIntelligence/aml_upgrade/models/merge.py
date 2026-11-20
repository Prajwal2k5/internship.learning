from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class MergeOperation(BaseModel):
    customer_id: str
    identity_key: str
    operation: Literal[
        "preserve_customer",
        "apply_vendor_change",
        "combine_changes",
        "skip_review_required",
        "skip_conflict",
        "skip_ambiguous",
        "skip_vendor_deletion",
    ]
    path: str = "$"
    reason: str


class MergeConflict(BaseModel):
    customer_id: str
    identity_key: str
    path: str
    standard_source_value: Any = None
    customer_source_value: Any = None
    standard_target_value: Any = None
    reason: str


class MergeReviewItem(BaseModel):
    customer_id: str
    identity_key: str
    classification: str
    reason: str
    standard_source_occurrences: int = 0
    customer_source_occurrences: int = 0
    standard_target_occurrences: int = 0


class MergedItem(BaseModel):
    customer_id: str
    identity_key: str
    payload: dict[str, Any]


class MergeResult(BaseModel):
    items: list[MergedItem] = Field(default_factory=list)
    operations: list[MergeOperation] = Field(default_factory=list)
    conflicts: list[MergeConflict] = Field(default_factory=list)
    review_queue: list[MergeReviewItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)
