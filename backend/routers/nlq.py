from fastapi import APIRouter
from pydantic import BaseModel

from services import nlq

router = APIRouter(prefix="/api/nlq", tags=["nlq"])


class NlqRequest(BaseModel):
    query: str


@router.post("")
def run_nlq(req: NlqRequest):
    return {"data": nlq.run(req.query)}
