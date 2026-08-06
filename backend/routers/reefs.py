from fastapi import APIRouter, HTTPException

from services import reefs

router = APIRouter(prefix="/api/reefs", tags=["reefs"])


@router.get("/{station_id}/bleaching-trend")
def bleaching_trend(station_id: str):
    result = reefs.bleaching_trend(station_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
