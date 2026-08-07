from fastapi import APIRouter, HTTPException

from services import data, trajectory

router = APIRouter(prefix="/api/species", tags=["species"])


@router.get("")
def list_species():
    media = data.species_media()
    return {
        "data": [
            {**s, "media": media.get(trajectory.species_id(s["sci"]))}
            for s in data.species()
        ]
    }


@router.get("/{species_id}/trajectory")
def species_trajectory(species_id: str):
    result = trajectory.trajectory(species_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result}
