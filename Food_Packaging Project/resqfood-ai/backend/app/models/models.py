"""
ResQFood AI — Database Models
All relational tables with proper constraints, indexes, and relationships.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, Date,
    ForeignKey, Enum as SQLEnum, Index, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    KITCHEN = "kitchen"
    NGO = "ngo"
    DRIVER = "driver"


class SurplusStatus(str, enum.Enum):
    ELIGIBLE = "eligible"
    URGENT = "urgent"
    REVIEW_REQUIRED = "review_required"
    EXPIRED = "expired"
    REJECTED = "rejected"
    ALLOCATED = "allocated"


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class UrgencyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class DeliveryStatus(str, enum.Enum):
    PLANNED = "planned"
    ASSIGNED = "assigned"
    PICKUP_IN_PROGRESS = "pickup_in_progress"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"


class StopStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"


class ScreeningStatus(str, enum.Enum):
    VISUAL_SCREENING_PASSED = "visual_screening_passed"
    REVIEW_REQUIRED = "review_required"
    SCREENING_UNAVAILABLE = "screening_unavailable"


def utcnow():
    return datetime.now(timezone.utc)


# ── Users ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    kitchen = relationship("Kitchen", back_populates="user", uselist=False)
    ngo = relationship("NGO", back_populates="user", uselist=False)
    driver = relationship("Driver", back_populates="user", uselist=False)
    sessions = relationship("UserSession", back_populates="user")


# ── User Sessions (WhatsApp state) ────────────────────────────────────
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), nullable=False)
    current_state = Column(String(100), default="idle")
    temporary_data = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="sessions")


# ── Kitchens ───────────────────────────────────────────────────────────
class Kitchen(Base):
    __tablename__ = "kitchens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    avg_daily_meals = Column(Integer, default=0)
    contact_person = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="kitchen")
    surplus_food = relationship("SurplusFood", back_populates="kitchen")
    consumption_history = relationship("FoodConsumptionHistory", back_populates="kitchen")
    predictions = relationship("DemandPrediction", back_populates="kitchen")


# ── NGOs ───────────────────────────────────────────────────────────────
class NGO(Base):
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity = Column(Integer, default=100)
    beneficiaries = Column(Integer, default=0)
    reliability_score = Column(Float, default=0.8)
    contact_person = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="ngo")
    requests = relationship("RecipientRequest", back_populates="ngo")


# ── Drivers ────────────────────────────────────────────────────────────
class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    vehicle_type = Column(String(100), nullable=True)
    license_number = Column(String(100), nullable=True)
    is_available = Column(Boolean, default=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="driver")
    deliveries = relationship("Delivery", back_populates="driver")


# ── Food Consumption History ──────────────────────────────────────────
class FoodConsumptionHistory(Base):
    __tablename__ = "food_consumption_history"

    id = Column(Integer, primary_key=True, index=True)
    kitchen_id = Column(Integer, ForeignKey("kitchens.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    meals_prepared = Column(Integer, nullable=False)
    meals_consumed = Column(Integer, nullable=False)
    meals_wasted = Column(Integer, default=0)
    event_type = Column(String(100), nullable=True)  # normal, holiday, exam, etc.
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    kitchen = relationship("Kitchen", back_populates="consumption_history")

    __table_args__ = (
        Index("idx_consumption_kitchen_date", "kitchen_id", "date"),
    )


# ── Demand Predictions ────────────────────────────────────────────────
class DemandPrediction(Base):
    __tablename__ = "demand_predictions"

    id = Column(Integer, primary_key=True, index=True)
    kitchen_id = Column(Integer, ForeignKey("kitchens.id"), nullable=False)
    prediction_date = Column(Date, nullable=False)
    predicted_demand = Column(Integer, nullable=False)
    recommended_production = Column(Integer, nullable=False)
    safety_buffer = Column(Integer, default=15)
    historical_average = Column(Float, nullable=True)
    model_type = Column(String(100), default="GradientBoostingRegressor")
    confidence_lower = Column(Integer, nullable=True)
    confidence_upper = Column(Integer, nullable=True)
    mae = Column(Float, nullable=True)  # Mean Absolute Error
    features_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    kitchen = relationship("Kitchen", back_populates="predictions")


# ── Surplus Food ──────────────────────────────────────────────────────
class SurplusFood(Base):
    __tablename__ = "surplus_food"

    id = Column(Integer, primary_key=True, index=True)
    kitchen_id = Column(Integer, ForeignKey("kitchens.id"), nullable=False)
    food_name = Column(String(255), nullable=False)
    food_category = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(50), default="meals")
    estimated_weight_kg = Column(Float, nullable=True)
    prepared_at = Column(DateTime, nullable=False)
    usable_until = Column(DateTime, nullable=False)
    storage_condition = Column(String(100), default="room_temperature")
    location = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(SurplusStatus), default=SurplusStatus.ELIGIBLE)
    screening_status = Column(SQLEnum(ScreeningStatus), default=ScreeningStatus.SCREENING_UNAVAILABLE)
    allocated_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    kitchen = relationship("Kitchen", back_populates="surplus_food")
    images = relationship("FoodImage", back_populates="surplus")
    requests = relationship("RecipientRequest", back_populates="surplus")
    allocations = relationship("AllocationResult", back_populates="surplus")

    __table_args__ = (
        Index("idx_surplus_status", "status"),
        Index("idx_surplus_kitchen", "kitchen_id"),
    )


# ── Food Images ───────────────────────────────────────────────────────
class FoodImage(Base):
    __tablename__ = "food_images"

    id = Column(Integer, primary_key=True, index=True)
    surplus_id = Column(Integer, ForeignKey("surplus_food.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    upload_source = Column(String(50), default="website")  # website or whatsapp
    screening_result = Column(SQLEnum(ScreeningStatus), default=ScreeningStatus.SCREENING_UNAVAILABLE)
    created_at = Column(DateTime, default=utcnow)

    surplus = relationship("SurplusFood", back_populates="images")


# ── Recipient Requests ────────────────────────────────────────────────
class RecipientRequest(Base):
    __tablename__ = "recipient_requests"

    id = Column(Integer, primary_key=True, index=True)
    ngo_id = Column(Integer, ForeignKey("ngos.id"), nullable=False)
    surplus_id = Column(Integer, ForeignKey("surplus_food.id"), nullable=False)
    requested_quantity = Column(Integer, nullable=False)
    urgency = Column(SQLEnum(UrgencyLevel), default=UrgencyLevel.MEDIUM)
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    allocated_quantity = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    ngo = relationship("NGO", back_populates="requests")
    surplus = relationship("SurplusFood", back_populates="requests")

    __table_args__ = (
        Index("idx_request_surplus", "surplus_id"),
        Index("idx_request_ngo", "ngo_id"),
    )


# ── Allocation Results ────────────────────────────────────────────────
class AllocationResult(Base):
    __tablename__ = "allocation_results"

    id = Column(Integer, primary_key=True, index=True)
    surplus_id = Column(Integer, ForeignKey("surplus_food.id"), nullable=False)
    request_id = Column(Integer, ForeignKey("recipient_requests.id"), nullable=False)
    ngo_id = Column(Integer, ForeignKey("ngos.id"), nullable=False)
    allocated_quantity = Column(Integer, nullable=False)
    priority_score = Column(Float, nullable=True)
    allocation_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    surplus = relationship("SurplusFood", back_populates="allocations")
    request = relationship("RecipientRequest")
    ngo = relationship("NGO")
    factors = relationship("AllocationFactor", back_populates="allocation")


# ── Allocation Factors ────────────────────────────────────────────────
class AllocationFactor(Base):
    __tablename__ = "allocation_factors"

    id = Column(Integer, primary_key=True, index=True)
    allocation_id = Column(Integer, ForeignKey("allocation_results.id"), nullable=False)
    factor_name = Column(String(100), nullable=False)
    factor_value = Column(Float, nullable=True)
    factor_label = Column(String(255), nullable=True)
    impact = Column(String(50), nullable=True)  # positive, negative, neutral
    created_at = Column(DateTime, default=utcnow)

    allocation = relationship("AllocationResult", back_populates="factors")


# ── Deliveries ────────────────────────────────────────────────────────
class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    surplus_id = Column(Integer, ForeignKey("surplus_food.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PLANNED)
    pickup_location = Column(Text, nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    total_meals = Column(Integer, default=0)
    total_weight_kg = Column(Float, default=0.0)
    total_stops = Column(Integer, default=0)
    estimated_duration_min = Column(Integer, nullable=True)
    route_sequence = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    driver = relationship("Driver", back_populates="deliveries")
    stops = relationship("DeliveryStop", back_populates="delivery", order_by="DeliveryStop.sequence_order")


# ── Delivery Stops ────────────────────────────────────────────────────
class DeliveryStop(Base):
    __tablename__ = "delivery_stops"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=False)
    allocation_id = Column(Integer, ForeignKey("allocation_results.id"), nullable=False)
    ngo_id = Column(Integer, ForeignKey("ngos.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    status = Column(SQLEnum(StopStatus), default=StopStatus.PENDING)
    priority = Column(String(50), nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    delivery = relationship("Delivery", back_populates="stops")
    allocation = relationship("AllocationResult")
    ngo = relationship("NGO")
    otp = relationship("DeliveryOTP", back_populates="stop", uselist=False)


# ── Delivery OTPs ─────────────────────────────────────────────────────
class DeliveryOTP(Base):
    __tablename__ = "delivery_otps"

    id = Column(Integer, primary_key=True, index=True)
    stop_id = Column(Integer, ForeignKey("delivery_stops.id"), unique=True, nullable=False)
    otp_code = Column(String(6), nullable=False)
    is_verified = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=utcnow)
    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    stop = relationship("DeliveryStop", back_populates="otp")


# ── Notifications ─────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info")
    is_read = Column(Boolean, default=False)
    channel = Column(String(50), default="web")  # web, whatsapp
    created_at = Column(DateTime, default=utcnow)


# ── Impact Metrics ────────────────────────────────────────────────────
class ImpactMetric(Base):
    __tablename__ = "impact_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    meals_rescued = Column(Integer, default=0)
    weight_rescued_kg = Column(Float, default=0.0)
    deliveries_completed = Column(Integer, default=0)
    recipients_served = Column(Integer, default=0)
    estimated_waste_prevented_kg = Column(Float, default=0.0)
    estimated_co2_saved_kg = Column(Float, default=0.0)
    estimated_water_saved_liters = Column(Float, default=0.0)
    estimated_cost_saved = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
