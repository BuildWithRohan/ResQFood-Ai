"""
ResQFood AI — Route / Delivery Optimizer
Determines the optimal delivery sequence considering distance, urgency,
and remaining usable time so food reaches recipients before expiry.

Uses a nearest-neighbour heuristic with priority weighting.
For the prototype, distance is computed as Haversine (straight-line).
"""
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone


@dataclass
class DeliveryPoint:
    ngo_id: int
    ngo_name: str
    allocation_id: int
    quantity: int
    address: Optional[str]
    latitude: float
    longitude: float
    urgency: str
    priority_score: float


@dataclass
class RouteStop:
    sequence: int
    ngo_id: int
    ngo_name: str
    allocation_id: int
    quantity: int
    address: Optional[str]
    latitude: float
    longitude: float
    urgency: str
    estimated_arrival_min: float  # minutes from start
    distance_from_prev_km: float


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def optimize_route(
    pickup_lat: float,
    pickup_lon: float,
    points: List[DeliveryPoint],
    avg_speed_kmh: float = 25.0,
    stop_overhead_min: float = 5.0,
) -> Tuple[List[RouteStop], float]:
    """
    Build an optimised delivery route from the kitchen to all recipients.

    Strategy: priority-weighted nearest-neighbour.
      - Among unvisited points, score each by:
            (1 / distance) × priority_weight
        and pick the highest-scoring next stop.
      - This balances proximity with urgency/priority so urgent,
        nearby stops are visited first.

    Returns: (ordered stops, total estimated duration in minutes)
    """
    if not points:
        return [], 0.0

    URGENCY_BOOST = {
        "low": 1.0, "medium": 1.2, "high": 1.5,
        "very_high": 2.0, "critical": 3.0,
    }

    remaining = list(range(len(points)))
    route: List[RouteStop] = []
    cur_lat, cur_lon = pickup_lat, pickup_lon
    elapsed_min = 0.0

    seq = 1
    while remaining:
        best_idx = None
        best_score = -1.0

        for i in remaining:
            p = points[i]
            dist = haversine(cur_lat, cur_lon, p.latitude, p.longitude)
            dist = max(dist, 0.1)  # avoid division by zero
            boost = URGENCY_BOOST.get(p.urgency, 1.0)
            score = (1.0 / dist) * boost * (1.0 + p.priority_score)
            if score > best_score:
                best_score = score
                best_idx = i

        p = points[best_idx]
        dist_km = haversine(cur_lat, cur_lon, p.latitude, p.longitude)
        travel_min = (dist_km / avg_speed_kmh) * 60
        elapsed_min += travel_min + stop_overhead_min

        route.append(RouteStop(
            sequence=seq,
            ngo_id=p.ngo_id,
            ngo_name=p.ngo_name,
            allocation_id=p.allocation_id,
            quantity=p.quantity,
            address=p.address,
            latitude=p.latitude,
            longitude=p.longitude,
            urgency=p.urgency,
            estimated_arrival_min=round(elapsed_min, 1),
            distance_from_prev_km=round(dist_km, 2),
        ))

        cur_lat, cur_lon = p.latitude, p.longitude
        remaining.remove(best_idx)
        seq += 1

    return route, round(elapsed_min, 1)
