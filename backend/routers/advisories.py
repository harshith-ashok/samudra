from fastapi import APIRouter

from services import data

router = APIRouter(prefix="/api/advisories", tags=["advisories"])


@router.get("")
def list_advisories(status: str | None = None):
    advisories = data.advisories()
    if status:
        advisories = [a for a in advisories if a["status"] == status]
    return {"data": advisories}
