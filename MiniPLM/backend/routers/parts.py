
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from backend.database import get_db
from backend.models import Part
from backend.schemas import PartCreate, PartUpdate, PartResponse

router = APIRouter(
    prefix="/parts",
    tags=["Parts"]
)


# 1. CREATE a new part
@router.post("/", response_model=PartResponse, status_code=201)
def create_part(
    part_data: PartCreate,
    db: Session = Depends(get_db)
):
    part_number = f"PLM-{uuid4().hex[:8].upper()}"

    new_part = Part(
        part_number=part_number,
        name=part_data.name,
        manufacturer=part_data.manufacturer,
        category=part_data.category,
        description=part_data.description,
        lifecycle_status=part_data.lifecycle_status
    )

    try:
        db.add(new_part)
        db.commit()
        db.refresh(new_part)
        return new_part

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create part due to a database conflict."
        )


# 2. GET all parts
@router.get("/", response_model=list[PartResponse])
def get_all_parts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters."
        )

    return (
        db.query(Part)
        .order_by(Part.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# 3. SEARCH parts
@router.get("/search", response_model=list[PartResponse])
def search_parts(
    q: str,
    db: Session = Depends(get_db)
):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty."
        )

    search_query = f"%{q.strip()}%"

    parts = db.query(Part).filter(
        (Part.name.ilike(search_query)) |
        (Part.part_number.ilike(search_query)) |
        (Part.manufacturer.ilike(search_query)) |
        (Part.category.ilike(search_query))
    ).all()

    return parts


# 4. GET a specific part by ID
@router.get("/{part_id}", response_model=PartResponse)
def get_part_by_id(
    part_id: int,
    db: Session = Depends(get_db)
):
    part = db.query(Part).filter(
        Part.id == part_id
    ).first()

    if not part:
        raise HTTPException(
            status_code=404,
            detail="Part not found."
        )

    return part


# 5. UPDATE an existing part
@router.put("/{part_id}", response_model=PartResponse)
def update_part(
    part_id: int,
    part_data: PartUpdate,
    db: Session = Depends(get_db)
):
    part = db.query(Part).filter(
        Part.id == part_id
    ).first()

    if not part:
        raise HTTPException(
            status_code=404,
            detail="Part not found."
        )

    update_data = part_data.model_dump(exclude_unset=True)

    required_fields = {
        "name",
        "manufacturer",
        "category",
        "lifecycle_status"
    }

    for field in required_fields:
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null."
            )

    for field, value in update_data.items():
        setattr(part, field, value)

    try:
        db.commit()
        db.refresh(part)
        return part

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update part due to a database conflict."
        )


# 6. DELETE an existing part
@router.delete("/{part_id}")
def delete_part(
    part_id: int,
    db: Session = Depends(get_db)
):
    part = db.query(Part).filter(
        Part.id == part_id
    ).first()

    if not part:
        raise HTTPException(
            status_code=404,
            detail="Part not found."
        )

    try:
        db.delete(part)
        db.commit()

        return {
            "message": "Part deleted successfully.",
            "part_id": part_id
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not delete part due to a database conflict."
        )
