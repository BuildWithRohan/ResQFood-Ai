"""
ResQFood AI — Pydantic Schemas
Request/response validation for all API endpoints.
"""
from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ───────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str
    role: str  # admin, kitchen, ngo, driver
    phone: Optional[str] = None
    # Role-specific fields
    kitchen_name: Optional[str] = None
    ngo_name: Optional[str] = None
    driver_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: Optional[int] = None
    vehicle_type: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ── Kitchen ────────────────────────────────────────────────────────────
class KitchenOut(BaseModel):
    id: int
    user_id: int
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_daily_meals: int = 0

    class Config:
        from_attributes = True


# ── NGO ────────────────────────────────────────────────────────────────
class NGOOut(BaseModel):
    id: int
    user_id: int
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int = 100
    beneficiaries: int = 0
    reliability_score: float = 0.8

    class Config:
        from_attributes = True


# ── Driver ─────────────────────────────────────────────────────────────
class DriverOut(BaseModel):
    id: int
    user_id: int
    name: str
    vehicle_type: Optional[str] = None
    is_available: bool = True

    class Config:
        from_attributes = True


# ── Consumption History ────────────────────────────────────────────────
class ConsumptionHistoryOut(BaseModel):
    id: int
    kitchen_id: int
    date: date
    day_of_week: int
    meals_prepared: int
    meals_consumed: int
    meals_wasted: int
    event_type: Optional[str] = None

    class Config:
        from_attributes = True


# ── Demand Prediction ─────────────────────────────────────────────────
class PredictionRequest(BaseModel):
    kitchen_id: int
    prediction_date: Optional[date] = None  # defaults to tomorrow


class PredictionOut(BaseModel):
    id: int
    kitchen_id: int
    prediction_date: date
    predicted_demand: int
    recommended_production: int
    safety_buffer: int
    historical_average: Optional[float] = None
    model_type: str = "GradientBoostingRegressor"
    confidence_lower: Optional[int] = None
    confidence_upper: Optional[int] = None
    mae: Optional[float] = None
    features_used: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Surplus Food ──────────────────────────────────────────────────────
class SurplusCreate(BaseModel):
    food_name: str
    food_category: Optional[str] = None
    quantity: int = Field(gt=0)
    unit: str = "meals"
    estimated_weight_kg: Optional[float] = None
    prepared_at: datetime
    usable_until: datetime
    storage_condition: str = "room_temperature"
    location: Optional[str] = None
    description: Optional[str] = None


class SurplusUpdate(BaseModel):
    status: Optional[str] = None
    quantity: Optional[int] = None
    usable_until: Optional[datetime] = None


class SurplusOut(BaseModel):
    id: int
    kitchen_id: int
    food_name: str
    food_category: Optional[str] = None
    quantity: int
    unit: str
    estimated_weight_kg: Optional[float] = None
    prepared_at: datetime
    usable_until: datetime
    storage_condition: str
    location: Optional[str] = None
    description: Optional[str] = None
    status: str
    screening_status: str
    allocated_quantity: int = 0
    remaining_quantity: int = 0
    remaining_minutes: Optional[float] = None
    kitchen_name: Optional[str] = None
    images: List["FoodImageOut"] = []
    created_at: datetime

    class Config:
        from_attributes = True


class FoodImageOut(BaseModel):
    id: int
    surplus_id: int
    image_path: str
    upload_source: str
    screening_result: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Recipient Requests ────────────────────────────────────────────────
class RequestCreate(BaseModel):
    surplus_id: int
    requested_quantity: int = Field(gt=0)
    urgency: str = "medium"
    notes: Optional[str] = None


class RequestUpdate(BaseModel):
    status: Optional[str] = None
    allocated_quantity: Optional[int] = None


class RequestOut(BaseModel):
    id: int
    ngo_id: int
    surplus_id: int
    requested_quantity: int
    urgency: str
    status: str
    allocated_quantity: int = 0
    notes: Optional[str] = None
    ngo_name: Optional[str] = None
    ngo_distance_km: Optional[float] = None
    food_name: Optional[str] = None
    remaining_minutes: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Allocation ─────────────────────────────────────────────────────────
class AllocationRun(BaseModel):
    surplus_id: int


class AllocationFactorOut(BaseModel):
    factor_name: str
    factor_value: Optional[float] = None
    factor_label: Optional[str] = None
    impact: Optional[str] = None

    class Config:
        from_attributes = True


class AllocationResultOut(BaseModel):
    id: int
    surplus_id: int
    request_id: int
    ngo_id: int
    allocated_quantity: int
    priority_score: Optional[float] = None
    allocation_reasoning: Optional[str] = None
    ngo_name: Optional[str] = None
    requested_quantity: Optional[int] = None
    urgency: Optional[str] = None
    distance_km: Optional[float] = None
    factors: List[AllocationFactorOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AllocationSummary(BaseModel):
    surplus_id: int
    food_name: str
    total_available: int
    total_requested: int
    total_allocated: int
    unfulfilled: int
    remaining_minutes: Optional[float] = None
    allocations: List[AllocationResultOut] = []


# ── Delivery ──────────────────────────────────────────────────────────
class DeliveryCreate(BaseModel):
    surplus_id: int
    driver_id: Optional[int] = None


class DeliveryStopOut(BaseModel):
    id: int
    delivery_id: int
    allocation_id: int
    ngo_id: int
    sequence_order: int
    quantity: int
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_arrival: Optional[datetime] = None
    status: str
    priority: Optional[str] = None
    ngo_name: Optional[str] = None
    otp_code: Optional[str] = None  # Only shown to NGO
    is_verified: Optional[bool] = None

    class Config:
        from_attributes = True


class DeliveryOut(BaseModel):
    id: int
    surplus_id: int
    driver_id: Optional[int] = None
    status: str
    pickup_location: Optional[str] = None
    total_meals: int = 0
    total_weight_kg: float = 0.0
    total_stops: int = 0
    estimated_duration_min: Optional[int] = None
    route_sequence: Optional[Any] = None
    stops: List[DeliveryStopOut] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeliveryUpdate(BaseModel):
    status: Optional[str] = None
    driver_id: Optional[int] = None


class StopUpdate(BaseModel):
    status: str


# ── OTP ───────────────────────────────────────────────────────────────
class OTPVerify(BaseModel):
    otp_code: str


class OTPResponse(BaseModel):
    stop_id: int
    otp_code: str
    ngo_name: str
    expires_at: datetime


# ── Analytics ─────────────────────────────────────────────────────────
class ImpactOut(BaseModel):
    total_meals_rescued: int = 0
    total_weight_rescued_kg: float = 0.0
    total_deliveries_completed: int = 0
    total_recipients_served: int = 0
    estimated_waste_prevented_kg: float = 0.0
    estimated_co2_saved_kg: float = 0.0
    estimated_water_saved_liters: float = 0.0
    estimated_cost_saved: float = 0.0
    active_surplus: int = 0
    active_requests: int = 0
    active_deliveries: int = 0
    registered_kitchens: int = 0
    registered_ngos: int = 0
    registered_drivers: int = 0


class AdminDashboard(BaseModel):
    impact: ImpactOut
    recent_surplus: List[SurplusOut] = []
    recent_allocations: List[AllocationResultOut] = []
    recent_deliveries: List[DeliveryOut] = []


# ── WhatsApp ──────────────────────────────────────────────────────────
class WhatsAppIncoming(BaseModel):
    From: Optional[str] = None
    Body: Optional[str] = None
    NumMedia: Optional[str] = "0"
    MediaUrl0: Optional[str] = None
    MediaContentType0: Optional[str] = None
