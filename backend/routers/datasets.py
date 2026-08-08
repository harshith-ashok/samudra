from fastapi import APIRouter, HTTPException

from services import datasets

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
def list_datasets():
    return {"data": datasets.list_datasets()}


@router.get("/{dataset_id}/records")
def get_records(dataset_id: str, search: str = "", sort: str | None = None, order: str = "asc"):
    try:
        return {"data": datasets.get_records(dataset_id, search=search, sort=sort, order=order)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no dataset '{dataset_id}'")


@router.get("/{dataset_id}/correlate")
def correlate(dataset_id: str, x: str, y: str):
    try:
        return {"data": datasets.correlate(dataset_id, x, y)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no dataset '{dataset_id}'")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
