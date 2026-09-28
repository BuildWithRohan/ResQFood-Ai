"""
Allocation API — runs the Smart Allocation Engine and persists results.
"""
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.schemas import (
    AllocationRun, AllocationResultOut, AllocationSummary,
    AllocationFactorOut,
)
from app.services.auth_service import get_current_user
from app.models.models import (
    User, SurplusFood, RecipientRequest, NGO, Kitchen,
    AllocationResult, AllocationFactor, SurplusStatus, RequestStatus,
)
from app.optimization.allocation_engine import (
    run_allocation, RequestInput,
)

router = APIRouter(prefix="/api/allocation", tags=["Allocation"])


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _remaining_min(surplus):
    now = datetime.now(timezone.utc)
    u = surplus.usable_until
    if u.tzinfo is None:
        u = u.replace(tzinfo=timezone.utc)
    return max(0, (u - now).total_seconds() / 60)


@router.post("/run", response_model=AllocationSummary)
def run_allocation_api(data: AllocationRun, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Execute the Smart Allocation Engine for a surplus item."""
    surplus = db.query(SurplusFood).filter(SurplusFood.id == data.surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")

    kitchen = db.query(Kitchen).filter(Kitchen.id == surplus.kitchen_id).first()

    # Get all pending requests for this surplus
    requests = db.query(RecipientRequest).filter(
        RecipientRequest.surplus_id == data.surplus_id,
        RecipientRequest.status == RequestStatus.PENDING.value,
    ).all()

    if not requests:
        raise HTTPException(status_code=400, detail="No pending requests for this surplus")

    remaining = _remaining_min(surplus)

    # Build request inputs
    req_inputs = []
    for req in requests:
        ngo = db.query(NGO).filter(NGO.id == req.ngo_id).first()
        if not ngo:
            continue

        distance = 3.0  # default
        if kitchen and ngo.latitude and kitchen.latitude:
            distance = round(_haversine(
                kitchen.latitude, kitchen.longitude,
                ngo.latitude, ngo.longitude
            ), 2)

        delivery_time = (distance / 25.0) * 60 + 5  # minutes

        req_inputs.append(RequestInput(
            request_id=req.id,
            ngo_id=ngo.id,
            ngo_name=ngo.name,
            requested_quantity=req.requested_quantity,
            urgency=req.urgency,
            distance_km=distance,
            delivery_time_min=round(delivery_time, 1),
            capacity=ngo.capacity,
            reliability=ngo.reliability_score,
            latitude=ngo.latitude,
            longitude=ngo.longitude,
        ))

    # Run the allocation engine
    result = run_allocation(
        surplus_id=surplus.id,
        food_name=surplus.food_name,
        available_quantity=surplus.remaining_quantity or surplus.quantity,
        remaining_minutes=remaining,
        requests=req_inputs,
    )

    # Persist allocation results
    db.query(AllocationResult).filter(AllocationResult.surplus_id == surplus.id).delete()
    db.query(AllocationFactor).filter(
        AllocationFactor.allocation_id.in_(
            db.query(AllocationResult.id).filter(AllocationResult.surplus_id == surplus.id)
        )
    ).delete(synchronize_session=False)

    allocation_outs = []
    for alloc in result.allocations:
        ar = AllocationResult(
            surplus_id=surplus.id,
            request_id=alloc.request_id,
            ngo_id=alloc.ngo_id,
            allocated_quantity=alloc.allocated_quantity,
            priority_score=alloc.priority_score,
            allocation_reasoning=alloc.reasoning,
        )
        db.add(ar)
        db.flush()

        # Persist factors
        for f in alloc.factors:
            af = AllocationFactor(
                allocation_id=ar.id,
                factor_name=f["factor_name"],
                factor_value=f.get("factor_value"),
                factor_label=f.get("factor_label"),
                impact=f.get("impact"),
            )
            db.add(af)

        # Update request
        req_obj = db.query(RecipientRequest).filter(RecipientRequest.id == alloc.request_id).first()
        if req_obj:
            req_obj.allocated_quantity = alloc.allocated_quantity
            if alloc.allocated_quantity >= alloc.requested_quantity:
                req_obj.status = RequestStatus.FULFILLED.value
            elif alloc.allocated_quantity > 0:
                req_obj.status = RequestStatus.PARTIALLY_FULFILLED.value
            else:
                req_obj.status = RequestStatus.REJECTED.value

        # Build output
        factors_out = [AllocationFactorOut(**f) for f in alloc.factors]
        allocation_outs.append(AllocationResultOut(
            id=ar.id,
            surplus_id=surplus.id,
            request_id=alloc.request_id,
            ngo_id=alloc.ngo_id,
            allocated_quantity=alloc.allocated_quantity,
            priority_score=alloc.priority_score,
            allocation_reasoning=alloc.reasoning,
            ngo_name=alloc.ngo_name,
            requested_quantity=alloc.requested_quantity,
            urgency=alloc.urgency,
            distance_km=alloc.distance_km,
            factors=factors_out,
            created_at=ar.created_at or datetime.now(timezone.utc),
        ))

    # Update surplus
    surplus.allocated_quantity = result.total_allocated
    surplus.remaining_quantity = max(0, surplus.quantity - result.total_allocated)
    surplus.status = SurplusStatus.ALLOCATED.value

    db.commit()

    return AllocationSummary(
        surplus_id=surplus.id,
        food_name=surplus.food_name,
        total_available=result.total_available,
        total_requested=result.total_requested,
        total_allocated=result.total_allocated,
        unfulfilled=result.unfulfilled,
        remaining_minutes=round(remaining, 1),
        allocations=allocation_outs,
    )


@router.get("/{surplus_id}", response_model=AllocationSummary)
def get_allocation(surplus_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Retrieve existing allocation results for a surplus item."""
    surplus = db.query(SurplusFood).filter(SurplusFood.id == surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")

    allocs = db.query(AllocationResult).filter(
        AllocationResult.surplus_id == surplus_id
    ).all()

    remaining = _remaining_min(surplus)

    allocation_outs = []
    total_requested = 0
    for ar in allocs:
        ngo = db.query(NGO).filter(NGO.id == ar.ngo_id).first()
        req = db.query(RecipientRequest).filter(RecipientRequest.id == ar.request_id).first()
        kitchen = db.query(Kitchen).filter(Kitchen.id == surplus.kitchen_id).first()

        distance = 3.0
        if kitchen and ngo and ngo.latitude and kitchen.latitude:
            distance = round(_haversine(kitchen.latitude, kitchen.longitude,
                                        ngo.latitude, ngo.longitude), 2)

        factors = db.query(AllocationFactor).filter(
            AllocationFactor.allocation_id == ar.id).all()

        requested = req.requested_quantity if req else 0
        total_requested += requested

        allocation_outs.append(AllocationResultOut(
            id=ar.id,
            surplus_id=surplus_id,
            request_id=ar.request_id,
            ngo_id=ar.ngo_id,
            allocated_quantity=ar.allocated_quantity,
            priority_score=ar.priority_score,
            allocation_reasoning=ar.allocation_reasoning,
            ngo_name=ngo.name if ngo else None,
            requested_quantity=requested,
            urgency=req.urgency if req else None,
            distance_km=distance,
            factors=[AllocationFactorOut.model_validate(f) for f in factors],
            created_at=ar.created_at,
        ))

    total_allocated = sum(a.allocated_quantity for a in allocation_outs)

    return AllocationSummary(
        surplus_id=surplus_id,
        food_name=surplus.food_name,
        total_available=surplus.quantity,
        total_requested=total_requested,
        total_allocated=total_allocated,
        unfulfilled=max(0, total_requested - total_allocated),
        remaining_minutes=round(remaining, 1),
        allocations=allocation_outs,
    )
