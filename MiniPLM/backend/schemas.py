
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal


# Allowed lifecycle statuses
LifecycleStatus = Literal[
    "Draft",
    "In Review",
    "Released",
    "Obsolete"
]


# Part creation request
class PartCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    manufacturer: str
    category: str
    description: Optional[str] = None
    lifecycle_status: LifecycleStatus = "Draft"


# Part update request
class PartUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    lifecycle_status: Optional[LifecycleStatus] = None


# Part API response
class PartResponse(BaseModel):
    id: int
    part_number: str
    name: str
    manufacturer: str
    category: str
    description: Optional[str] = None
    lifecycle_status: str

    model_config = ConfigDict(from_attributes=True)


# AI description request
class AIDescriptionRequest(BaseModel):
    name: str
    category: str
    manufacturer: str


# AI description response
class AIDescriptionResponse(BaseModel):
    generated_description: str


# Document API response
class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    content_type: str

    model_config = ConfigDict(from_attributes=True)
