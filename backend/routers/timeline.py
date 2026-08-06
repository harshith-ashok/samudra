from fastapi import APIRouter, HTTPException

from services import timeline as timeline_service

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/{metric}")
def get_timeline(metric: str, days: int = 30):
    result = timeline_service.timeline(metric, days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
