
from pydantic import BaseModel, Field


class AMLIdentityRecord(BaseModel):
    customer_id: str
    snapshot_name: str
    source_file: str

    item_type: str | None = None
    item_id: str | None = None
    action: str | None = None

    identity_key: str | None = None
    parent_identity_key: str | None = None
    nesting_path: str

    is_top_level: bool = False
    is_query: bool = False


class DuplicateIdentityGroup(BaseModel):
    customer_id: str
    snapshot_name: str
    identity_key: str
    occurrences: list[AMLIdentityRecord] = Field(default_factory=list)


class IdentityInventory(BaseModel):
    records: list[AMLIdentityRecord] = Field(default_factory=list)
    query_records: list[AMLIdentityRecord] = Field(default_factory=list)
    duplicate_groups: list[DuplicateIdentityGroup] = Field(default_factory=list)
    missing_identity_records: list[AMLIdentityRecord] = Field(default_factory=list)
