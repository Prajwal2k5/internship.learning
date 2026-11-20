
from pydantic import BaseModel, Field


class AMLReference(BaseModel):
    """A reference from one AML property to another AML item."""

    element_name: str
    target_id: str | None = None
    target_type: str | None = None
    keyed_name: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class AMLField(BaseModel):
    """A property or nested XML field belonging to an AML item."""

    name: str
    value: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    reference: AMLReference | None = None
    children: list["AMLField"] = Field(default_factory=list)
    items: list["NormalizedAMLItem"] = Field(default_factory=list)


class NormalizedAMLItem(BaseModel):
    """Structured representation of one AML Item."""

    item_type: str | None = None
    item_id: str | None = None
    action: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    fields: list[AMLField] = Field(default_factory=list)
    relationships: list["NormalizedAMLItem"] = Field(default_factory=list)


class AMLDocument(BaseModel):
    """Structured representation of an AML XML document."""

    source_file: str
    root_element: str
    items: list[NormalizedAMLItem] = Field(default_factory=list)


AMLField.model_rebuild()
NormalizedAMLItem.model_rebuild()
