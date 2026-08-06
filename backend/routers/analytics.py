from fastapi import APIRouter

from services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/catch-vs-sst")
def catch_vs_sst():
    return {"data": analytics.catch_vs_sst()}


@router.get("/biodiversity-index")
def biodiversity_index():
    return {"data": analytics.biodiversity_index()}


@router.get("/compliance-trend")
def compliance_trend():
    return {"data": analytics.compliance_trend()}


@router.get("/vessel-activity")
def vessel_activity():
    return {"data": analytics.vessel_activity()}
