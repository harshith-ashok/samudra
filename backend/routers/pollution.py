from fastapi import APIRouter

from services import pollution

router = APIRouter(prefix="/api/pollution", tags=["pollution"])


@router.get("")
def list_pollution():
    return {"data": pollution.list_plants()}
