from fastapi import APIRouter, HTTPException, Query

from services import predict

router = APIRouter(prefix="/api/predict", tags=["predict"])


@router.get("/stock")
def stock(
    species: str = "Sardinella longiceps",
    region: str = "Kerala coast",
    months_ahead: int = 6,
    sst_delta: float = Query(0.0, ge=-3, le=3, description="What-if: SST anomaly in °C (Phase 21 scenario simulator)"),
    fishing_pressure: float = Query(1.0, ge=0.3, le=3.0, description="What-if: fishing pressure multiplier (Phase 21 scenario simulator)"),
):
    result = predict.stock_forecast(species, region, months_ahead, sst_delta, fishing_pressure)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}


@router.get("/bleaching")
def bleaching(station_id: str = "lakshadweep"):
    result = predict.bleaching_risk(station_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}


@router.get("/range-shift")
def range_shift(
    species: str = "Thunnus albacares",
    sst_delta: float = Query(0.0, ge=-3, le=3, description="What-if: SST anomaly in °C (Phase 21 scenario simulator)"),
):
    result = predict.range_shift(species, sst_delta)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
