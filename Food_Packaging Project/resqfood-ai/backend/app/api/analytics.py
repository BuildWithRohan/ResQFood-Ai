"""
Analytics / Impact API — aggregates rescued meals, waste prevented,
environmental estimates, and system-wide metrics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.schemas.schemas import ImpactOut, AdminDashboard, SurplusOut, AllocationResultOut, DeliveryOut
from app.services.auth_service import get_current_user
from app.models.models import (
    User, Kitchen, NGO, Driver,
    SurplusFood, RecipientRequest, AllocationResult,
    Delivery, DeliveryStop, DeliveryOTP, DeliveryStatus, StopStatus, SurplusStatus,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Estimated impact multipliers (clearly labelled as estimates)
CO2_PER_KG_FOOD = 2.5       # kg CO2 per kg food waste avoided
WATER_PER_KG_FOOD = 1000.0  # liters per kg food
COST_PER_MEAL = 35.0        # INR per meal


@router.get("/impact", response_model=ImpactOut)
def get_impact(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Compute system-wide impact metrics."""
    # Delivered stops
    delivered_stops = db.query(DeliveryStop).filter(
        DeliveryStop.status == StopStatus.DELIVERED.value
    ).all()

    meals_rescued = sum(s.quantity for s in delivered_stops)
    deliveries_completed = db.query(Delivery).filter(
        Delivery.status == DeliveryStatus.DELIVERED.value
    ).count()

    # Weight from surplus items that were allocated
    allocated_surplus = db.query(SurplusFood).filter(
        SurplusFood.status == SurplusStatus.ALLOCATED.value
    ).all()
    weight_rescued = sum(s.estimated_weight_kg or 0 for s in allocated_surplus)

    # Count unique NGOs served
    recipients_served = db.query(func.count(func.distinct(DeliveryStop.ngo_id))).filter(
        DeliveryStop.status == StopStatus.DELIVERED.value
    ).scalar() or 0

    # Active counts
    active_surplus = db.query(SurplusFood).filter(
        SurplusFood.status.in_([SurplusStatus.ELIGIBLE.value, SurplusStatus.URGENT.value])
    ).count()

    active_requests = db.query(RecipientRequest).filter(
        RecipientRequest.status == "pending"
    ).count()

    active_deliveries = db.query(Delivery).filter(
        Delivery.status.in_([
            DeliveryStatus.PLANNED.value,
            DeliveryStatus.ASSIGNED.value,
            DeliveryStatus.PICKUP_IN_PROGRESS.value,
            DeliveryStatus.IN_TRANSIT.value,
        ])
    ).count()

    return ImpactOut(
        total_meals_rescued=meals_rescued,
        total_weight_rescued_kg=round(weight_rescued, 2),
        total_deliveries_completed=deliveries_completed,
        total_recipients_served=recipients_served,
        estimated_waste_prevented_kg=round(weight_rescued, 2),
        estimated_co2_saved_kg=round(weight_rescued * CO2_PER_KG_FOOD, 2),
        estimated_water_saved_liters=round(weight_rescued * WATER_PER_KG_FOOD, 2),
        estimated_cost_saved=round(meals_rescued * COST_PER_MEAL, 2),
        active_surplus=active_surplus,
        active_requests=active_requests,
        active_deliveries=active_deliveries,
        registered_kitchens=db.query(Kitchen).count(),
        registered_ngos=db.query(NGO).count(),
        registered_drivers=db.query(Driver).count(),
    )


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Complete admin dashboard data."""
    impact = get_impact(db=db, user=user)

    recent_surplus = db.query(SurplusFood).order_by(SurplusFood.created_at.desc()).limit(10).all()
    recent_deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).limit(10).all()
    recent_allocs = db.query(AllocationResult).order_by(AllocationResult.created_at.desc()).limit(10).all()

    return {
        "impact": impact,
        "recent_surplus": [
            {c.name: getattr(s, c.name) for c in s.__table__.columns}
            for s in recent_surplus
        ],
        "recent_deliveries": [
            {c.name: getattr(d, c.name) for c in d.__table__.columns}
            for d in recent_deliveries
        ],
        "recent_allocations": [
            {c.name: getattr(a, c.name) for c in a.__table__.columns}
            for a in recent_allocs
        ],
    }
