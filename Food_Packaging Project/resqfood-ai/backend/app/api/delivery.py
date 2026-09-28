"""
Delivery API — create deliveries with route optimization, driver assignment,
stop management, and OTP verification.
"""
import random
import string
import math
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.schemas import (
    DeliveryCreate, DeliveryOut, DeliveryUpdate, DeliveryStopOut,
    StopUpdate, OTPVerify, OTPResponse,
)
from app.services.auth_service import get_current_user
from app.models.models import (
    User, Driver, Kitchen, NGO, SurplusFood,
    AllocationResult, Delivery, DeliveryStop, DeliveryOTP,
    DeliveryStatus, StopStatus,
)
from app.optimization.route_optimizer import (
    optimize_route, DeliveryPoint,
)

router = APIRouter(prefix="/api/deliveries", tags=["Deliveries"])


def _enrich_stop(stop: DeliveryStop, db: Session, show_otp_for_ngo_id: int = None) -> dict:
    ngo = db.query(NGO).filter(NGO.id == stop.ngo_id).first()
    otp = db.query(DeliveryOTP).filter(DeliveryOTP.stop_id == stop.id).first()
    d = {c.name: getattr(stop, c.name) for c in stop.__table__.columns}
    d["ngo_name"] = ngo.name if ngo else None
    d["otp_code"] = otp.otp_code if otp and show_otp_for_ngo_id == stop.ngo_id else None
    d["is_verified"] = otp.is_verified if otp else None
    return d


def _enrich_delivery(delivery: Delivery, db: Session, ngo_id: int = None) -> dict:
    stops = db.query(DeliveryStop).filter(
        DeliveryStop.delivery_id == delivery.id
    ).order_by(DeliveryStop.sequence_order).all()

    d = {c.name: getattr(delivery, c.name) for c in delivery.__table__.columns}
    d["stops"] = [_enrich_stop(s, db, ngo_id) for s in stops]
    return d


@router.post("/", response_model=DeliveryOut)
def create_delivery(data: DeliveryCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Create a delivery with optimized route from allocation results."""
    surplus = db.query(SurplusFood).filter(SurplusFood.id == data.surplus_id).first()
    if not surplus:
        raise HTTPException(status_code=404, detail="Surplus not found")

    kitchen = db.query(Kitchen).filter(Kitchen.id == surplus.kitchen_id).first()
    allocations = db.query(AllocationResult).filter(
        AllocationResult.surplus_id == data.surplus_id,
        AllocationResult.allocated_quantity > 0,
    ).all()

    if not allocations:
        raise HTTPException(status_code=400, detail="No allocations to deliver")

    # Assign driver
    driver_id = data.driver_id
    if not driver_id:
        driver = db.query(Driver).filter(Driver.is_available == True).first()
        if driver:
            driver_id = driver.id

    # Build delivery points for route optimization
    points = []
    for alloc in allocations:
        ngo = db.query(NGO).filter(NGO.id == alloc.ngo_id).first()
        if ngo and alloc.allocated_quantity > 0:
            points.append(DeliveryPoint(
                ngo_id=ngo.id,
                ngo_name=ngo.name,
                allocation_id=alloc.id,
                quantity=alloc.allocated_quantity,
                address=ngo.address,
                latitude=ngo.latitude or 12.97,
                longitude=ngo.longitude or 77.59,
                urgency=alloc.request.urgency if alloc.request else "medium",
                priority_score=alloc.priority_score or 0,
            ))

    # Optimize route
    pickup_lat = kitchen.latitude if kitchen else 12.9716
    pickup_lon = kitchen.longitude if kitchen else 77.5946
    route_stops, total_duration = optimize_route(pickup_lat, pickup_lon, points)

    # Create delivery
    total_meals = sum(p.quantity for p in points)
    delivery = Delivery(
        surplus_id=surplus.id,
        driver_id=driver_id,
        status=DeliveryStatus.PLANNED,
        pickup_location=kitchen.address if kitchen else "Kitchen",
        pickup_latitude=pickup_lat,
        pickup_longitude=pickup_lon,
        total_meals=total_meals,
        total_weight_kg=surplus.estimated_weight_kg or 0,
        total_stops=len(route_stops),
        estimated_duration_min=int(total_duration),
        route_sequence=[{"ngo_id": s.ngo_id, "name": s.ngo_name, "seq": s.sequence} for s in route_stops],
    )
    db.add(delivery)
    db.flush()

    # Create delivery stops with OTPs
    now = datetime.now(timezone.utc)
    for rs in route_stops:
        est_arrival = now + timedelta(minutes=rs.estimated_arrival_min)
        stop = DeliveryStop(
            delivery_id=delivery.id,
            allocation_id=rs.allocation_id,
            ngo_id=rs.ngo_id,
            sequence_order=rs.sequence,
            quantity=rs.quantity,
            address=rs.address,
            latitude=rs.latitude,
            longitude=rs.longitude,
            estimated_arrival=est_arrival,
            status=StopStatus.PENDING,
            priority=rs.urgency,
        )
        db.add(stop)
        db.flush()

        # Generate OTP for each stop
        otp_code = ''.join(random.choices(string.digits, k=6))
        otp = DeliveryOTP(
            stop_id=stop.id,
            otp_code=otp_code,
            expires_at=est_arrival + timedelta(hours=2),
        )
        db.add(otp)

    db.commit()
    db.refresh(delivery)
    return DeliveryOut.model_validate(_enrich_delivery(delivery, db))


@router.get("/", response_model=List[DeliveryOut])
def list_deliveries(driver_id: int = None, status: str = None,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    query = db.query(Delivery)
    if driver_id:
        query = query.filter(Delivery.driver_id == driver_id)
    if status:
        query = query.filter(Delivery.status == status)
    deliveries = query.order_by(Delivery.created_at.desc()).all()

    # Check if user is NGO — show OTP only to their own stops
    ngo = db.query(NGO).filter(NGO.user_id == user.id).first()
    ngo_id = ngo.id if ngo else None

    return [DeliveryOut.model_validate(_enrich_delivery(d, db, ngo_id)) for d in deliveries]


@router.get("/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    ngo = db.query(NGO).filter(NGO.user_id == user.id).first()
    ngo_id = ngo.id if ngo else None
    return DeliveryOut.model_validate(_enrich_delivery(delivery, db, ngo_id))


@router.patch("/{delivery_id}", response_model=DeliveryOut)
def update_delivery(delivery_id: int, data: DeliveryUpdate,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    if data.status:
        delivery.status = data.status
        if data.status == DeliveryStatus.PICKUP_IN_PROGRESS.value:
            delivery.started_at = datetime.now(timezone.utc)
        elif data.status == DeliveryStatus.DELIVERED.value:
            delivery.completed_at = datetime.now(timezone.utc)
    if data.driver_id:
        delivery.driver_id = data.driver_id
    db.commit()
    db.refresh(delivery)
    return DeliveryOut.model_validate(_enrich_delivery(delivery, db))


@router.patch("/{delivery_id}/stops/{stop_id}", response_model=DeliveryStopOut)
def update_stop(delivery_id: int, stop_id: int, data: StopUpdate,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    stop = db.query(DeliveryStop).filter(
        DeliveryStop.id == stop_id,
        DeliveryStop.delivery_id == delivery_id,
    ).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    stop.status = data.status
    if data.status == StopStatus.ARRIVED.value:
        stop.arrived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stop)
    return DeliveryStopOut.model_validate(_enrich_stop(stop, db))


# ── OTP endpoints ─────────────────────────────────────────────────────
@router.post("/{delivery_id}/stops/{stop_id}/generate-otp", response_model=OTPResponse)
def generate_otp(delivery_id: int, stop_id: int,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    stop = db.query(DeliveryStop).filter(
        DeliveryStop.id == stop_id,
        DeliveryStop.delivery_id == delivery_id,
    ).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    otp = db.query(DeliveryOTP).filter(DeliveryOTP.stop_id == stop.id).first()
    if not otp:
        otp_code = ''.join(random.choices(string.digits, k=6))
        otp = DeliveryOTP(
            stop_id=stop.id,
            otp_code=otp_code,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        db.add(otp)
        db.commit()
        db.refresh(otp)

    ngo = db.query(NGO).filter(NGO.id == stop.ngo_id).first()
    return OTPResponse(
        stop_id=stop.id,
        otp_code=otp.otp_code,
        ngo_name=ngo.name if ngo else "Unknown",
        expires_at=otp.expires_at,
    )


@router.post("/{delivery_id}/stops/{stop_id}/verify-otp")
def verify_otp(delivery_id: int, stop_id: int, data: OTPVerify,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    stop = db.query(DeliveryStop).filter(
        DeliveryStop.id == stop_id,
        DeliveryStop.delivery_id == delivery_id,
    ).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    otp = db.query(DeliveryOTP).filter(DeliveryOTP.stop_id == stop.id).first()
    if not otp:
        raise HTTPException(status_code=400, detail="OTP not generated")

    if otp.is_verified:
        return {"message": "Already verified", "verified": True}

    now = datetime.now(timezone.utc)
    expires = otp.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        raise HTTPException(status_code=400, detail="OTP has expired")

    if otp.otp_code != data.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Verify
    otp.is_verified = True
    otp.verified_at = now
    stop.status = StopStatus.DELIVERED.value
    stop.delivered_at = now

    # Check if all stops are delivered
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    all_stops = db.query(DeliveryStop).filter(DeliveryStop.delivery_id == delivery_id).all()
    all_delivered = all(s.status == StopStatus.DELIVERED.value for s in all_stops)
    if all_delivered:
        delivery.status = DeliveryStatus.DELIVERED.value
        delivery.completed_at = now

    db.commit()
    return {
        "message": "OTP verified successfully. Delivery confirmed!",
        "verified": True,
        "stop_id": stop.id,
        "all_delivered": all_delivered,
    }
