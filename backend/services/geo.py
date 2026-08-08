"""Small geo helpers shared across services — haversine was previously
duplicated in services/trajectory.py; pulled out here once a second caller
(services/ocean_point.py) needed the exact same formula.
"""

import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
