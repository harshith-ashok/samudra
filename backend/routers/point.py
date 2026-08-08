from fastapi import APIRouter, HTTPException, Query

from services import ocean_point

router = APIRouter(prefix="/api/point", tags=["point"])


@router.get("")
def get_point(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    result = ocean_point.estimate(lat, lng)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
