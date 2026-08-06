from fastapi import APIRouter

from services import data

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


@router.get("")
def list_glossary():
    return {"data": data.glossary()}
