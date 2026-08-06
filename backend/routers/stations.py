from fastapi import APIRouter, HTTPException

from services import data

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("")
def list_stations():
    stations = [
        {k: v for k, v in s.items() if k != "history"}
        for s in data.stations()
    ]
    return {"data": stations}


@router.get("/{station_id}")
def get_station(station_id: str):
    station = data.station_by_id(station_id.lower())
    if not station:
        raise HTTPException(status_code=404, detail=f"no station '{station_id}'")
    return {"data": station}
