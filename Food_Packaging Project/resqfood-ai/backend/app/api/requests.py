"""Recipient Requests API — NGOs request surplus food."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import math

from app.database import get_db
from app.schemas.schemas import RequestCreate, RequestUpdate, RequestOut
from app.services.auth_service import get_current_user
from app.models.models import (
    User, NGO, SurplusFood, RecipientRequest, Kitchen, RequestStatus, UrgencyLevel
)

router = APIRouter(prefix="/api/requests", tags=["Requests"])


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _remaining_min(surplus):
    now = datetime.now(timezone.utc)
    u = surplus.usable_until
    if u.tzinfo is None:
        u = u.replace(tzinfo=timezone.utc)
    return max(0, (u - now).total_seconds() / 60)


def _enrich_request(req: RecipientRequest, db: Session) -> dict:
    ngo = db.query(NGO).filter(NGO.id == req.ngo_id).first()
    surplus = db.query(SurplusFood).filter(SurplusFood.id == req.surplus_id).first()
    kitchen = db.query(Kitchen).filter(Kitchen.id == surplus.kitchen_id).first() if surplus else None

    distance = None
    if ngo and kitchen and ngo.latitude and kitchen.latitude:
        distance = round(_haversine(kitchen.latitude, kitchen.longitude, ngo.latitude, ngo.longitude), 2)

    return {
        **{c.name: getattr(req, c.name) for c in req.__table__.columns},
        "ngo_name": ngo.name if ngo else None,
        "ngo_distance_km": distance,
        "food_name": surplus.food_name if surplus else None,
        "remaining_minutes": round(_remaining_min(surplus), 1) if surplus else None,
    }


@router.post("/", response_model=RequestOut)
def create_request(data: RequestCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    ngo = db.query(NGO).filter(NGO.user_id == user.id).first()
    if not ngo:
        raise HTTPException(status_code=403, detail="User is not associated with an NGO")

    surplus = db.query(SurplusFood).filter(SurplusFood.id == data.surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")

    req = RecipientRequest(
        ngo_id=ngo.id,
        surplus_id=data.surplus_id,
        requested_quantity=data.requested_quantity,
        urgency=data.urgency,
        notes=data.notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return RequestOut.model_validate(_enrich_request(req, db))


@router.get("/", response_model=List[RequestOut])
def list_requests(surplus_id: int = None, ngo_id: int = None, status: str = None,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    query = db.query(RecipientRequest)
    if surplus_id:
        query = query.filter(RecipientRequest.surplus_id == surplus_id)
    if ngo_id:
        query = query.filter(RecipientRequest.ngo_id == ngo_id)
    if status:
        query = query.filter(RecipientRequest.status == status)

    results = query.order_by(RecipientRequest.created_at.desc()).all()
    return [RequestOut.model_validate(_enrich_request(r, db)) for r in results]


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    req = db.query(RecipientRequest).filter(RecipientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return RequestOut.model_validate(_enrich_request(req, db))


@router.patch("/{request_id}", response_model=RequestOut)
def update_request(request_id: int, data: RequestUpdate,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    req = db.query(RecipientRequest).filter(RecipientRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if data.status:
        req.status = data.status
    if data.allocated_quantity is not None:
        req.allocated_quantity = data.allocated_quantity
    db.commit()
    db.refresh(req)
    return RequestOut.model_validate(_enrich_request(req, db))
