
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class FileRecord(BaseModel):
    customer_id: str
    snapshot_name: str
    relative_path: str
    file_name: str
    size_bytes: int
    sha256: str
    xml_valid: bool
    root_element: str | None = None
    validation_error: str | None = None


class SnapshotRecord(BaseModel):
    snapshot_name: str
    directory_present: bool
    files: list[FileRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CustomerRecord(BaseModel):
    customer_id: str
    snapshots: list[SnapshotRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ScanManifest(BaseModel):
    schema_version: str = "1.0"
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    input_root: str
    customers: list[CustomerRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
