from fastapi import APIRouter
from pydantic import BaseModel

from services import translate

router = APIRouter(prefix="/api/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str = "auto"


@router.post("")
def translate_text(req: TranslateRequest):
    translated = translate.translate(req.text, req.target_lang, req.source_lang)
    return {"data": {"translated_text": translated, "target_lang": req.target_lang}}
