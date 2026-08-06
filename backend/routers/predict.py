from fastapi import APIRouter, HTTPException

from services import predict

router = APIRouter(prefix="/api/predict", tags=["predict"])


@router.get("/stock")
def stock(species: str = "Sardinella longiceps", region: str = "Kerala coast", months_ahead: int = 6):
    result = predict.stock_forecast(species, region, months_ahead)
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
def range_shift(species: str = "Thunnus albacares"):
    result = predict.range_shift(species)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
