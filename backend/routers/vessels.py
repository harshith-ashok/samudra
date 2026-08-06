from fastapi import APIRouter

from services import vessels

router = APIRouter(prefix="/api/vessels", tags=["vessels"])


@router.get("")
def list_vessels():
    return {"data": vessels.list_vessels()}
