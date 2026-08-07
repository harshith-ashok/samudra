from fastapi import APIRouter
from pydantic import BaseModel

from services import rag

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    station_context: dict | None = None
    species_context: dict | None = None


@router.post("")
def chat(req: ChatRequest):
    result = rag.answer(req.message, station_context=req.station_context, species_context=req.species_context)
    return {"data": result}
