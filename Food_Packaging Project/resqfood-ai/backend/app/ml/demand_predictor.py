"""
ResQFood AI — ML Demand Prediction Engine
Uses GradientBoostingRegressor trained on historical consumption data.

Features:
  - day_of_week (one-hot)
  - rolling averages (7-day, 14-day)
  - previous day demand
  - day-over-day delta
  - is_weekend flag

The model predicts expected demand; the system adds a configurable safety
buffer to compute recommended production.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error
from datetime import date, timedelta
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DemandPredictor:
    """
    ML-based demand prediction from historical consumption records.
    """

    def __init__(self, safety_buffer: int = 15):
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )
        self.safety_buffer = safety_buffer
        self.is_trained = False
        self.mae: Optional[float] = None
        self.feature_names: list = []

    # ── Feature Engineering ────────────────────────────────────────────
    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw consumption history into ML features."""
        df = df.sort_values("date").copy()
        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Rolling averages
        df["rolling_7"] = df["meals_consumed"].rolling(window=7, min_periods=1).mean()
        df["rolling_14"] = df["meals_consumed"].rolling(window=14, min_periods=1).mean()
        df["rolling_3"] = df["meals_consumed"].rolling(window=3, min_periods=1).mean()

        # Lag features
        df["prev_day"] = df["meals_consumed"].shift(1)
        df["prev_2_day"] = df["meals_consumed"].shift(2)
        df["delta_1"] = df["meals_consumed"].diff(1)

        # Week number (cyclical)
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

        # One-hot encode day_of_week
        for d in range(7):
            df[f"dow_{d}"] = (df["day_of_week"] == d).astype(int)

        df = df.dropna().reset_index(drop=True)
        return df

    def _feature_cols(self) -> list:
        return [
            "is_weekend",
            "rolling_7", "rolling_14", "rolling_3",
            "prev_day", "prev_2_day", "delta_1",
            "week_of_year",
            "dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6",
        ]

    # ── Training ───────────────────────────────────────────────────────
    def train(self, history: list[dict]) -> Dict[str, Any]:
        """
        Train the model on historical consumption records.

        Each record: {"date": date, "meals_consumed": int, ...}
        Returns training metrics.
        """
        if len(history) < 14:
            raise ValueError("Need at least 14 days of history to train a reliable model")

        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"])
        df = self._build_features(df)

        self.feature_names = self._feature_cols()
        X = df[self.feature_names].values
        y = df["meals_consumed"].values

        # Train
        self.model.fit(X, y)
        self.is_trained = True

        # Evaluate with cross-validation
        if len(df) >= 20:
            cv_scores = cross_val_score(self.model, X, y, cv=min(5, len(df) // 4),
                                        scoring="neg_mean_absolute_error")
            self.mae = -cv_scores.mean()
        else:
            preds = self.model.predict(X)
            self.mae = mean_absolute_error(y, preds)

        return {
            "model_type": "GradientBoostingRegressor",
            "training_samples": len(df),
            "mae": round(self.mae, 2),
            "features_used": self.feature_names,
        }

    # ── Prediction ─────────────────────────────────────────────────────
    def predict(
        self,
        history: list[dict],
        target_date: date,
    ) -> Dict[str, Any]:
        """
        Predict demand for a given date using recent history.

        Returns predicted demand, recommended production, and metadata.
        """
        if not self.is_trained:
            self.train(history)

        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Build a row for the target date using recent stats
        recent = df.tail(14)
        target_dow = target_date.weekday()

        feature_row = {
            "is_weekend": 1 if target_dow >= 5 else 0,
            "rolling_7": recent.tail(7)["meals_consumed"].mean(),
            "rolling_14": recent["meals_consumed"].mean(),
            "rolling_3": recent.tail(3)["meals_consumed"].mean(),
            "prev_day": recent.iloc[-1]["meals_consumed"] if len(recent) > 0 else 800,
            "prev_2_day": recent.iloc[-2]["meals_consumed"] if len(recent) > 1 else 800,
            "delta_1": (recent.iloc[-1]["meals_consumed"] - recent.iloc[-2]["meals_consumed"])
                       if len(recent) > 1 else 0,
            "week_of_year": target_date.isocalendar()[1],
        }
        for d in range(7):
            feature_row[f"dow_{d}"] = 1 if target_dow == d else 0

        X_pred = np.array([[feature_row[f] for f in self.feature_names]])
        predicted = max(0, int(round(self.model.predict(X_pred)[0])))

        # Recommended production = predicted + safety buffer
        recommended = predicted + self.safety_buffer

        # Historical average
        hist_avg = round(df["meals_consumed"].mean(), 1)

        # Confidence interval (approximate: prediction ± MAE)
        mae = self.mae or 20
        confidence_lower = max(0, int(predicted - 1.5 * mae))
        confidence_upper = int(predicted + 1.5 * mae)

        # Potential waste prevented
        potential_surplus_avoided = max(0, int(hist_avg) - recommended)

        return {
            "predicted_demand": predicted,
            "recommended_production": recommended,
            "safety_buffer": self.safety_buffer,
            "historical_average": hist_avg,
            "confidence_lower": confidence_lower,
            "confidence_upper": confidence_upper,
            "mae": round(mae, 2),
            "model_type": "GradientBoostingRegressor",
            "potential_surplus_avoided": potential_surplus_avoided,
            "features_used": self.feature_names,
            "prediction_date": str(target_date),
        }


# Singleton predictor instance per kitchen (simple cache)
_predictors: Dict[int, DemandPredictor] = {}


def get_predictor(kitchen_id: int, safety_buffer: int = 15) -> DemandPredictor:
    if kitchen_id not in _predictors:
        _predictors[kitchen_id] = DemandPredictor(safety_buffer=safety_buffer)
    return _predictors[kitchen_id]
