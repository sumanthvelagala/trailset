import math


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return straight-line distance in miles between two lat/lng points."""
    R = 3958.8  # Earth radius in miles
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def travel_time_minutes(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Estimate travel time in minutes assuming driving at ~20mph in city traffic."""
    miles = haversine_miles(lat1, lng1, lat2, lng2)
    if miles < 0.3:
        # Walking distance: ~20 min per mile
        return max(5, int(miles * 20))
    # Driving: ~20mph with stops
    return max(5, int((miles / 20) * 60))
