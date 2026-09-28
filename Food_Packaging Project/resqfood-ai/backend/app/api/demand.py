"""Demand Prediction API — train model, predict, list predictions & history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta

from app.database import get_db
from app.schemas.schemas import PredictionRequest, PredictionOut, ConsumptionHistoryOut
from app.services.auth_service import get_current_user
from app.models.models import (
    User, Kitchen, FoodConsumptionHistory, DemandPrediction
)
from app.ml.demand_predictor import get_predictor
from app.config import settings

router = APIRouter(prefix="/api/demand", tags=["Demand Prediction"])


@router.post("/predict", response_model=PredictionOut)
def predict_demand(data: PredictionRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Run ML demand prediction for a kitchen."""
    kitchen = db.query(Kitchen).filter(Kitchen.id == data.kitchen_id).first()
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")

    # Fetch historical consumption
    history = db.query(FoodConsumptionHistory).filter(
        FoodConsumptionHistory.kitchen_id == data.kitchen_id
    ).order_by(FoodConsumptionHistory.date).all()

    if len(history) < 14:
        raise HTTPException(status_code=400, detail="Need at least 14 days of history")

    history_dicts = [
        {"date": h.date, "meals_consumed": h.meals_consumed, "day_of_week": h.day_of_week}
        for h in history
    ]

    target = data.prediction_date or (date.today() + timedelta(days=1))
    predictor = get_predictor(data.kitchen_id, settings.SAFETY_BUFFER_MEALS)
    result = predictor.predict(history_dicts, target)

    # Save prediction
    pred = DemandPrediction(
        kitchen_id=data.kitchen_id,
        prediction_date=target,
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
    db.add(pred)
    db.commit()
    db.refresh(pred)

    return PredictionOut.model_validate(pred)


@router.get("/predictions", response_model=List[PredictionOut])
def list_predictions(kitchen_id: int = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    query = db.query(DemandPrediction)
    if kitchen_id:
        query = query.filter(DemandPrediction.kitchen_id == kitchen_id)
    return [PredictionOut.model_validate(p) for p in query.order_by(DemandPrediction.created_at.desc()).limit(20).all()]


@router.get("/history", response_model=List[ConsumptionHistoryOut])
def get_history(kitchen_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    records = db.query(FoodConsumptionHistory).filter(
        FoodConsumptionHistory.kitchen_id == kitchen_id
    ).order_by(FoodConsumptionHistory.date).all()
    return [ConsumptionHistoryOut.model_validate(r) for r in records]
