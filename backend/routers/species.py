from fastapi import APIRouter

from services import data

router = APIRouter(prefix="/api/species", tags=["species"])


@router.get("")
def list_species():
    return {"data": data.species()}
