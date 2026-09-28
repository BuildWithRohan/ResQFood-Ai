"""
ResQFood AI — Smart Allocation Engine
Uses Google OR-Tools (CP-SAT solver) for constrained optimization.

Objective: Maximize total food rescued weighted by urgency, time feasibility,
and delivery proximity — ensuring food reaches recipients before expiry.

Inputs per request:
  - requested_quantity
  - urgency score
  - remaining usable time (minutes)
  - estimated delivery time (from distance)
  - recipient capacity
  - recipient reliability score

The solver assigns integer quantities to each request subject to:
  1. Total allocated ≤ available supply
  2. Each allocation ≤ requested quantity
  3. Each allocation ≤ recipient capacity
  4. Delivery must be feasible (delivery_time < remaining_time)

Each allocation is weighted by a composite priority score so the solver
maximises the amount of food rescued in the most impactful order.
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ortools.sat.python import cp_model
import logging

logger = logging.getLogger(__name__)


# ── Data structures ────────────────────────────────────────────────────
@dataclass
class RequestInput:
    request_id: int
    ngo_id: int
    ngo_name: str
    requested_quantity: int
    urgency: str              # low / medium / high / very_high / critical
    distance_km: float
    delivery_time_min: float  # estimated minutes for delivery
    capacity: int             # how many meals the NGO can handle
    reliability: float        # 0–1
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class AllocationOutput:
    request_id: int
    ngo_id: int
    ngo_name: str
    allocated_quantity: int
    requested_quantity: int
    priority_score: float
    urgency: str
    distance_km: float
    delivery_feasible: bool
    reasoning: str
    factors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AllocationSummary:
    surplus_id: int
    food_name: str
    total_available: int
    total_requested: int
    total_allocated: int
    unfulfilled: int
    remaining_minutes: float
    allocations: List[AllocationOutput] = field(default_factory=list)


# ── Helper maps ────────────────────────────────────────────────────────
URGENCY_WEIGHT = {
    "low": 1.0,
    "medium": 2.0,
    "high": 3.5,
    "very_high": 5.0,
    "critical": 7.0,
}


def _estimate_delivery_time(distance_km: float, avg_speed_kmh: float = 25.0) -> float:
    """Estimated travel time in minutes (includes 5-min stop overhead)."""
    return (distance_km / avg_speed_kmh) * 60 + 5


def _compute_priority(req: RequestInput, remaining_minutes: float) -> float:
    """
    Composite priority score (higher = should be served first).

    Components:
      urgency_score   (0–7)   × 30 %
      time_pressure   (0–5)   × 25 %   — less remaining time → higher score
      proximity       (0–5)   × 20 %   — closer → higher score
      reliability     (0–1)   × 15 %
      feasibility     (0–5)   × 10 %   — delivery within window gets bonus
    """
    urgency_score = URGENCY_WEIGHT.get(req.urgency, 2.0)

    # Time pressure: ratio of delivery time to remaining time
    if remaining_minutes <= 0:
        time_pressure = 0.0
    else:
        time_ratio = req.delivery_time_min / remaining_minutes
        if time_ratio > 1.0:
            time_pressure = 0.0  # not feasible
        else:
            time_pressure = 5.0 * (1.0 - time_ratio)  # tighter window → higher score

    # Proximity: inverse of distance (capped at 5)
    proximity = min(5.0, 5.0 / max(req.distance_km, 0.5))

    # Feasibility bonus
    feasible = req.delivery_time_min < remaining_minutes
    feasibility = 5.0 if feasible else 0.0

    score = (
        urgency_score * 0.30 +
        time_pressure * 0.25 +
        proximity * 0.20 +
        req.reliability * 5.0 * 0.15 +
        feasibility * 0.10
    )
    return round(score, 4)


# ── Main allocation engine ────────────────────────────────────────────
def run_allocation(
    surplus_id: int,
    food_name: str,
    available_quantity: int,
    remaining_minutes: float,
    requests: List[RequestInput],
) -> AllocationSummary:
    """
    Run the Smart Allocation Engine on a set of competing requests.

    Uses OR-Tools CP-SAT to maximise weighted rescued meals.
    """
    if not requests:
        return AllocationSummary(
            surplus_id=surplus_id,
            food_name=food_name,
            total_available=available_quantity,
            total_requested=0,
            total_allocated=0,
            unfulfilled=0,
            remaining_minutes=remaining_minutes,
        )

    # Pre-compute delivery times and priority scores
    for req in requests:
        if req.delivery_time_min <= 0:
            req.delivery_time_min = _estimate_delivery_time(req.distance_km)

    priorities = []
    feasibilities = []
    for req in requests:
        p = _compute_priority(req, remaining_minutes)
        f = req.delivery_time_min < remaining_minutes
        priorities.append(p)
        feasibilities.append(f)

    total_requested = sum(r.requested_quantity for r in requests)

    # ── Build OR-Tools CP-SAT model ───────────────────────────────────
    model = cp_model.CpModel()
    n = len(requests)

    # Decision variables: how many meals to allocate to each request
    alloc_vars = []
    for i, req in enumerate(requests):
        upper = min(req.requested_quantity, req.capacity, available_quantity)
        if not feasibilities[i]:
            upper = 0  # infeasible deliveries get zero
        var = model.NewIntVar(0, max(0, upper), f"alloc_{i}")
        alloc_vars.append(var)

    # Constraint: total allocated ≤ available
    model.Add(sum(alloc_vars) <= available_quantity)

    # Objective: maximise Σ (priority_i × alloc_i)
    # Multiply priorities by 1000 and round to keep integer arithmetic
    int_priorities = [int(p * 1000) for p in priorities]
    model.Maximize(
        sum(int_priorities[i] * alloc_vars[i] for i in range(n))
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    allocations: List[AllocationOutput] = []
    total_allocated = 0

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, req in enumerate(requests):
            qty = solver.Value(alloc_vars[i])
            total_allocated += qty

            # Generate per-request factors and reasoning
            factors = _build_factors(req, priorities[i], feasibilities[i],
                                     remaining_minutes, qty)
            reasoning = _build_reasoning(req, priorities[i], feasibilities[i],
                                         remaining_minutes, qty, available_quantity)

            allocations.append(AllocationOutput(
                request_id=req.request_id,
                ngo_id=req.ngo_id,
                ngo_name=req.ngo_name,
                allocated_quantity=qty,
                requested_quantity=req.requested_quantity,
                priority_score=priorities[i],
                urgency=req.urgency,
                distance_km=req.distance_km,
                delivery_feasible=feasibilities[i],
                reasoning=reasoning,
                factors=factors,
            ))
    else:
        # Fallback: simple priority-based greedy
        logger.warning("OR-Tools solver did not find optimal; falling back to greedy.")
        indexed = sorted(range(n), key=lambda i: priorities[i], reverse=True)
        remaining = available_quantity
        for i in indexed:
            req = requests[i]
            if not feasibilities[i]:
                qty = 0
            else:
                qty = min(req.requested_quantity, req.capacity, remaining)
                remaining -= qty
            total_allocated += qty
            factors = _build_factors(req, priorities[i], feasibilities[i],
                                     remaining_minutes, qty)
            reasoning = _build_reasoning(req, priorities[i], feasibilities[i],
                                         remaining_minutes, qty, available_quantity)
            allocations.append(AllocationOutput(
                request_id=req.request_id,
                ngo_id=req.ngo_id,
                ngo_name=req.ngo_name,
                allocated_quantity=qty,
                requested_quantity=req.requested_quantity,
                priority_score=priorities[i],
                urgency=req.urgency,
                distance_km=req.distance_km,
                delivery_feasible=feasibilities[i],
                reasoning=reasoning,
                factors=factors,
            ))

    # Sort by priority (highest first) for display
    allocations.sort(key=lambda a: a.priority_score, reverse=True)

    return AllocationSummary(
        surplus_id=surplus_id,
        food_name=food_name,
        total_available=available_quantity,
        total_requested=total_requested,
        total_allocated=total_allocated,
        unfulfilled=max(0, total_requested - total_allocated),
        remaining_minutes=remaining_minutes,
        allocations=allocations,
    )


# ── Explainability helpers ─────────────────────────────────────────────
def _build_factors(
    req: RequestInput,
    priority: float,
    feasible: bool,
    remaining_min: float,
    allocated: int,
) -> List[Dict[str, Any]]:
    """Build a list of factor dicts explaining the allocation decision."""
    factors = [
        {
            "factor_name": "urgency",
            "factor_value": URGENCY_WEIGHT.get(req.urgency, 2.0),
            "factor_label": f"Urgency: {req.urgency.replace('_', ' ').title()}",
            "impact": "positive" if URGENCY_WEIGHT.get(req.urgency, 2.0) >= 3.0 else "neutral",
        },
        {
            "factor_name": "distance",
            "factor_value": req.distance_km,
            "factor_label": f"Distance: {req.distance_km} km",
            "impact": "positive" if req.distance_km <= 2.0 else ("negative" if req.distance_km > 5 else "neutral"),
        },
        {
            "factor_name": "delivery_time",
            "factor_value": round(req.delivery_time_min, 1),
            "factor_label": f"Est. delivery time: {int(req.delivery_time_min)} min",
            "impact": "positive" if req.delivery_time_min < remaining_min * 0.5 else "neutral",
        },
        {
            "factor_name": "delivery_feasibility",
            "factor_value": 1.0 if feasible else 0.0,
            "factor_label": "Delivery feasible before expiry" if feasible else "Delivery may NOT reach before expiry",
            "impact": "positive" if feasible else "negative",
        },
        {
            "factor_name": "remaining_time",
            "factor_value": round(remaining_min, 1),
            "factor_label": f"Remaining usable time: {int(remaining_min)} min",
            "impact": "positive" if remaining_min > 60 else ("negative" if remaining_min < 30 else "neutral"),
        },
        {
            "factor_name": "capacity",
            "factor_value": float(req.capacity),
            "factor_label": f"Recipient capacity: {req.capacity} meals",
            "impact": "positive" if req.capacity >= req.requested_quantity else "neutral",
        },
        {
            "factor_name": "reliability",
            "factor_value": req.reliability,
            "factor_label": f"Reliability score: {req.reliability:.0%}",
            "impact": "positive" if req.reliability >= 0.8 else "neutral",
        },
        {
            "factor_name": "priority_score",
            "factor_value": priority,
            "factor_label": f"Composite priority score: {priority:.2f}",
            "impact": "positive" if priority >= 3.0 else "neutral",
        },
    ]
    return factors


def _build_reasoning(
    req: RequestInput,
    priority: float,
    feasible: bool,
    remaining_min: float,
    allocated: int,
    total_available: int,
) -> str:
    """Generate a human-readable explanation of the allocation decision."""
    parts = []

    if allocated == 0 and not feasible:
        parts.append(f"{req.ngo_name} received 0 meals because delivery is not feasible before the food expires.")
        parts.append(f"Estimated delivery time ({int(req.delivery_time_min)} min) exceeds remaining usable time ({int(remaining_min)} min).")
        return " ".join(parts)

    if allocated == 0:
        parts.append(f"{req.ngo_name} received 0 meals — insufficient remaining supply after higher-priority allocations.")
        return " ".join(parts)

    if allocated == req.requested_quantity:
        parts.append(f"{req.ngo_name} received full requested quantity ({allocated} meals).")
    elif allocated < req.requested_quantity:
        parts.append(f"{req.ngo_name} received {allocated} of {req.requested_quantity} requested meals (partial allocation).")

    # Urgency
    if req.urgency in ("very_high", "critical"):
        parts.append(f"Received higher priority due to {req.urgency.replace('_', ' ')} urgency.")
    elif req.urgency == "high":
        parts.append("High urgency contributed positively to allocation priority.")
    else:
        parts.append(f"Urgency level ({req.urgency}) was moderate.")

    # Distance
    if req.distance_km <= 2.0:
        parts.append(f"Short delivery distance ({req.distance_km} km) favoured this allocation.")
    elif req.distance_km >= 5.0:
        parts.append(f"Longer delivery distance ({req.distance_km} km) reduced allocation priority.")

    # Time feasibility
    if feasible:
        margin = remaining_min - req.delivery_time_min
        parts.append(f"Delivery feasible with ~{int(margin)} min margin before expiry.")
    else:
        parts.append("Delivery feasibility was marginal.")

    # Reliability
    if req.reliability >= 0.9:
        parts.append(f"High recipient reliability ({req.reliability:.0%}) supported allocation.")

    return " ".join(parts)
