from fastapi import APIRouter, HTTPException, Query

from services import reefs

router = APIRouter(prefix="/api/reefs", tags=["reefs"])


@router.get("/{station_id}/bleaching-trend")
def bleaching_trend(
    station_id: str,
    sst_delta: float = Query(0.0, ge=-3, le=3, description="What-if: SST anomaly in °C (Phase 21 scenario simulator)"),
    chlorophyll_delta: float = Query(0.0, ge=-0.5, le=0.5, description="What-if: chlorophyll-a delta in mg/m3 (Phase 21 scenario simulator)"),
):
    result = reefs.bleaching_trend(station_id, sst_delta, chlorophyll_delta)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
