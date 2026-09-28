# -*- coding: utf-8 -*-
"""
ResQFood AI -- Seed Data Script
Creates realistic demo data for the mandatory demonstration scenario.

Run: python seed/seed_data.py
"""
import sys
import os
import random
from datetime import datetime, date, timedelta, timezone

# Add backend to path
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
except NameError:
    sys.path.insert(0, os.getcwd())

from app.database import engine, SessionLocal, Base
from app.models.models import (
    User, Kitchen, NGO, Driver, FoodConsumptionHistory,
    DemandPrediction, SurplusFood, RecipientRequest,
    UserSession, SurplusStatus, UrgencyLevel, RequestStatus,
)
from app.services.auth_service import hash_password
from app.ml.demand_predictor import get_predictor
from app.config import settings


def seed():
    """Create all seed data for the demo."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing data
        for model in [
            UserSession, RecipientRequest, DemandPrediction,
            FoodConsumptionHistory, SurplusFood,
            Driver, NGO, Kitchen, User,
        ]:
            db.query(model).delete()
        db.commit()
        print("[OK] Cleared existing data")

        # -- 1. Users --
        admin_user = User(
            email="admin@resqfood.ai",
            password_hash=hash_password("admin123"),
            full_name="System Admin",
            role="admin",
            phone="+919900000001",
        )
        kitchen_user = User(
            email="kitchen@abccollege.edu",
            password_hash=hash_password("kitchen123"),
            full_name="Rajesh Kumar",
            role="kitchen",
            phone="+919900000002",
        )
        ngo_a_user = User(
            email="ngo_a@feedindia.org",
            password_hash=hash_password("ngoa123"),
            full_name="Priya Sharma",
            role="ngo",
            phone="+919900000003",
        )
        ngo_b_user = User(
            email="ngo_b@mealshare.org",
            password_hash=hash_password("ngob123"),
            full_name="Amit Patel",
            role="ngo",
            phone="+919900000004",
        )
        ngo_c_user = User(
            email="ngo_c@foodrescue.in",
            password_hash=hash_password("ngoc123"),
            full_name="Sunita Reddy",
            role="ngo",
            phone="+919900000005",
        )
        driver_user = User(
            email="driver@resqfood.ai",
            password_hash=hash_password("driver123"),
            full_name="Vikram Singh",
            role="driver",
            phone="+919900000006",
        )

        db.add_all([admin_user, kitchen_user, ngo_a_user, ngo_b_user, ngo_c_user, driver_user])
        db.flush()
        print("[OK] Created 6 users (admin, kitchen, 3 NGOs, driver)")

        # -- 2. Kitchen --
        kitchen = Kitchen(
            user_id=kitchen_user.id,
            name="ABC College Cafeteria",
            address="123 College Road, Koramangala, Bangalore 560034",
            latitude=12.9352,
            longitude=77.6245,
            avg_daily_meals=800,
            contact_person="Rajesh Kumar",
        )
        db.add(kitchen)
        db.flush()
        print("[OK] Created kitchen: ABC College Cafeteria")

        # -- 3. NGOs --
        ngo_a = NGO(
            user_id=ngo_a_user.id,
            name="Feed India Foundation",
            address="45 MG Road, Bangalore 560001",
            latitude=12.9716,
            longitude=77.5946,
            capacity=50,
            beneficiaries=200,
            reliability_score=0.92,
            contact_person="Priya Sharma",
        )
        ngo_b = NGO(
            user_id=ngo_b_user.id,
            name="MealShare Network",
            address="78 Whitefield, Bangalore 560066",
            latitude=12.9698,
            longitude=77.7500,
            capacity=80,
            beneficiaries=350,
            reliability_score=0.78,
            contact_person="Amit Patel",
        )
        ngo_c = NGO(
            user_id=ngo_c_user.id,
            name="Food Rescue India",
            address="12 Indiranagar, Bangalore 560038",
            latitude=12.9784,
            longitude=77.6408,
            capacity=30,
            beneficiaries=120,
            reliability_score=0.95,
            contact_person="Sunita Reddy",
        )
        db.add_all([ngo_a, ngo_b, ngo_c])
        db.flush()
        print("[OK] Created 3 NGOs (Feed India, MealShare, Food Rescue)")

        # -- 4. Driver --
        driver = Driver(
            user_id=driver_user.id,
            name="Vikram Singh",
            vehicle_type="bike",
            license_number="KA01AB1234",
            is_available=True,
            current_latitude=12.9352,
            current_longitude=77.6245,
        )
        db.add(driver)
        db.flush()
        print("[OK] Created driver: Vikram Singh")

        # -- 5. Historical Consumption Data (90 days) --
        today = date.today()
        base_demand = 800
        history_records = []

        for i in range(90, 0, -1):
            d = today - timedelta(days=i)
            dow = d.weekday()

            # Realistic variations
            if dow == 6:  # Sunday
                base = int(base_demand * 0.55)
            elif dow == 5:  # Saturday
                base = int(base_demand * 0.70)
            elif dow == 0:  # Monday
                base = int(base_demand * 0.95)
            else:
                base = base_demand

            # Add noise
            noise = random.randint(-40, 40)
            # Occasional events
            if random.random() < 0.05:
                noise -= random.randint(80, 150)  # holiday/low day
            elif random.random() < 0.08:
                noise += random.randint(30, 80)   # event day

            consumed = max(200, base + noise)
            prepared = consumed + random.randint(10, 60)
            wasted = prepared - consumed

            event = None
            if consumed < base - 100:
                event = "holiday"
            elif consumed > base + 50:
                event = "event"

            record = FoodConsumptionHistory(
                kitchen_id=kitchen.id,
                date=d,
                day_of_week=dow,
                meals_prepared=prepared,
                meals_consumed=consumed,
                meals_wasted=max(0, wasted),
                event_type=event,
            )
            history_records.append(record)

        db.add_all(history_records)
        db.flush()
        print("[OK] Created %d days of consumption history" % len(history_records))

        # -- 6. Run Demand Prediction --
        history_dicts = [
            {"date": r.date, "meals_consumed": r.meals_consumed, "day_of_week": r.day_of_week}
            for r in history_records
        ]

        predictor = get_predictor(kitchen.id, settings.SAFETY_BUFFER_MEALS)
        tomorrow = today + timedelta(days=1)
        result = predictor.predict(history_dicts, tomorrow)

        prediction = DemandPrediction(
            kitchen_id=kitchen.id,
            prediction_date=tomorrow,
            predicted_demand=result["predicted_demand"],
            recommended_production=result["recommended_production"],
            safety_buffer=result["safety_buffer"],
            historical_average=result["historical_average"],
            model_type=result["model_type"],
            confidence_lower=result["confidence_lower"],
            confidence_upper=result["confidence_upper"],
            mae=result["mae"],
            features_used=result["features_used"],
        )
        db.add(prediction)
        db.flush()
        print("[OK] Demand prediction: %d meals, recommended: %d meals (MAE: %.1f)" % (
            result['predicted_demand'], result['recommended_production'], result['mae']))

        # -- 7. Surplus Food --
        now = datetime.now(timezone.utc)
        surplus = SurplusFood(
            kitchen_id=kitchen.id,
            food_name="Vegetable Biryani",
            food_category="rice_dish",
            quantity=40,
            unit="meals",
            estimated_weight_kg=12.0,
            prepared_at=now - timedelta(minutes=30),
            usable_until=now + timedelta(hours=3),
            storage_condition="room_temperature",
            location="ABC College Cafeteria, 123 College Road, Koramangala",
            description="Fresh vegetable biryani with raita, prepared for lunch. "
                        "Surplus due to lower-than-expected attendance.",
            status=SurplusStatus.ELIGIBLE,
            remaining_quantity=40,
        )
        db.add(surplus)
        db.flush()
        print("[OK] Created surplus: 40 meals Vegetable Biryani (3h window)")

        # -- 8. NGO Requests (competing) --
        req_a = RecipientRequest(
            ngo_id=ngo_a.id,
            surplus_id=surplus.id,
            requested_quantity=15,
            urgency=UrgencyLevel.HIGH,
            status=RequestStatus.PENDING,
            notes="Need for evening distribution at MG Road shelter",
        )
        req_b = RecipientRequest(
            ngo_id=ngo_b.id,
            surplus_id=surplus.id,
            requested_quantity=30,
            urgency=UrgencyLevel.MEDIUM,
            status=RequestStatus.PENDING,
            notes="For community kitchen in Whitefield",
        )
        req_c = RecipientRequest(
            ngo_id=ngo_c.id,
            surplus_id=surplus.id,
            requested_quantity=10,
            urgency=UrgencyLevel.VERY_HIGH,
            status=RequestStatus.PENDING,
            notes="Urgent: Children's home running low on food",
        )
        db.add_all([req_a, req_b, req_c])
        db.flush()
        print("[OK] Created 3 competing requests (15 + 30 + 10 = 55 meals for 40 available)")

        db.commit()
        print("")
        print("=" * 60)
        print("  SEED DATA COMPLETE")
        print("=" * 60)
        print("")
        print("Login credentials:")
        print("  Admin:   admin@resqfood.ai    / admin123")
        print("  Kitchen: kitchen@abccollege.edu / kitchen123")
        print("  NGO A:   ngo_a@feedindia.org   / ngoa123")
        print("  NGO B:   ngo_b@mealshare.org   / ngob123")
        print("  NGO C:   ngo_c@foodrescue.in   / ngoc123")
        print("  Driver:  driver@resqfood.ai    / driver123")
        print("")
        print("Demo scenario ready:")
        print("  Historical avg: ~%.0f meals/day" % result['historical_average'])
        print("  Predicted demand: %d meals" % result['predicted_demand'])
        print("  Recommended production: %d meals" % result['recommended_production'])
        print("  Surplus: 40 meals Vegetable Biryani")
        print("  Requests: 55 meals (NGO A=15, B=30, C=10)")
        print("  Available: 40 meals -> 15 meals unfulfillable")
        print("")
        print("Next: Run allocation via POST /api/allocation/run")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print("Error: %s" % str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
