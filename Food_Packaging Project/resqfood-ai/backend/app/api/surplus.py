"""Surplus Food API — CRUD + image upload + eligibility status."""
import os
import uuid
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.schemas import SurplusCreate, SurplusUpdate, SurplusOut, FoodImageOut
from app.services.auth_service import get_current_user
from app.models.models import (
    User, Kitchen, SurplusFood, FoodImage, SurplusStatus, ScreeningStatus
)
from app.config import settings

router = APIRouter(prefix="/api/surplus", tags=["Surplus Food"])


def _compute_status(surplus: SurplusFood) -> str:
    """Determine food eligibility status based on remaining time."""
    now = datetime.now(timezone.utc)
    usable_until = surplus.usable_until
    if usable_until.tzinfo is None:
        usable_until = usable_until.replace(tzinfo=timezone.utc)
    remaining = (usable_until - now).total_seconds() / 60

    if remaining <= 0:
        return SurplusStatus.EXPIRED.value
    if remaining <= 30:
        return SurplusStatus.URGENT.value
    if surplus.screening_status == ScreeningStatus.REVIEW_REQUIRED.value:
        return SurplusStatus.REVIEW_REQUIRED.value
    return SurplusStatus.ELIGIBLE.value


def _remaining_minutes(surplus: SurplusFood) -> float:
    now = datetime.now(timezone.utc)
    usable_until = surplus.usable_until
    if usable_until.tzinfo is None:
        usable_until = usable_until.replace(tzinfo=timezone.utc)
    return max(0, (usable_until - now).total_seconds() / 60)


def _enrich(surplus: SurplusFood, db: Session) -> dict:
    """Build SurplusOut dict with computed fields."""
    kitchen = db.query(Kitchen).filter(Kitchen.id == surplus.kitchen_id).first()
    images = db.query(FoodImage).filter(FoodImage.surplus_id == surplus.id).all()
    d = {
        **{c.name: getattr(surplus, c.name) for c in surplus.__table__.columns},
        "remaining_minutes": round(_remaining_minutes(surplus), 1),
        "kitchen_name": kitchen.name if kitchen else None,
        "images": [FoodImageOut.model_validate(img) for img in images],
        "status": surplus.status if surplus.status != SurplusStatus.ALLOCATED.value else surplus.status,
    }
    return d


@router.post("/", response_model=SurplusOut)
def create_surplus(data: SurplusCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    kitchen = db.query(Kitchen).filter(Kitchen.user_id == user.id).first()
    if not kitchen:
        raise HTTPException(status_code=403, detail="User is not associated with a kitchen")

    surplus = SurplusFood(
        kitchen_id=kitchen.id,
        food_name=data.food_name,
        food_category=data.food_category,
        quantity=data.quantity,
        unit=data.unit,
        estimated_weight_kg=data.estimated_weight_kg,
        prepared_at=data.prepared_at,
        usable_until=data.usable_until,
        storage_condition=data.storage_condition,
        location=data.location or kitchen.address,
        description=data.description,
        remaining_quantity=data.quantity,
    )
    surplus.status = _compute_status(surplus)
    db.add(surplus)
    db.commit()
    db.refresh(surplus)
    return SurplusOut.model_validate(_enrich(surplus, db))


@router.get("/", response_model=List[SurplusOut])
def list_surplus(status: str = None, kitchen_id: int = None,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    query = db.query(SurplusFood)
    if kitchen_id:
        query = query.filter(SurplusFood.kitchen_id == kitchen_id)
    if status:
        query = query.filter(SurplusFood.status == status)

    results = query.order_by(SurplusFood.created_at.desc()).all()

    # Update statuses dynamically
    enriched = []
    for s in results:
        new_status = _compute_status(s)
        if s.status not in (SurplusStatus.ALLOCATED.value, SurplusStatus.REJECTED.value):
            if s.status != new_status:
                s.status = new_status
                db.add(s)
        enriched.append(SurplusOut.model_validate(_enrich(s, db)))
    db.commit()
    return enriched


@router.get("/{surplus_id}", response_model=SurplusOut)
def get_surplus(surplus_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    surplus = db.query(SurplusFood).filter(SurplusFood.id == surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")
    return SurplusOut.model_validate(_enrich(surplus, db))


@router.patch("/{surplus_id}", response_model=SurplusOut)
def update_surplus(surplus_id: int, data: SurplusUpdate,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    surplus = db.query(SurplusFood).filter(SurplusFood.id == surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")
    if data.status:
        surplus.status = data.status
    if data.quantity is not None:
        surplus.quantity = data.quantity
    if data.usable_until:
        surplus.usable_until = data.usable_until
    db.commit()
    db.refresh(surplus)
    return SurplusOut.model_validate(_enrich(surplus, db))


@router.post("/{surplus_id}/image")
def upload_image(surplus_id: int, file: UploadFile = File(...),
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    surplus = db.query(SurplusFood).filter(SurplusFood.id == surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    img = FoodImage(
        surplus_id=surplus_id,
        image_path=f"/uploads/{filename}",
        uploaded_by=user.id,
        upload_source="website",
        screening_result=ScreeningStatus.SCREENING_UNAVAILABLE,
    )
    db.add(img)

    # Update surplus screening to passed (visual screening assistance)
    surplus.screening_status = ScreeningStatus.VISUAL_SCREENING_PASSED
    db.commit()
    db.refresh(img)

    return {"id": img.id, "image_path": img.image_path, "status": "uploaded"}
