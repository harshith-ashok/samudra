from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services import stt

router = APIRouter(prefix="/api/stt", tags=["stt"])


@router.post("")
async def transcribe(audio: UploadFile = File(...), language: str = Form(stt.DEFAULT_LANGUAGE)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="empty audio upload")
    text = stt.transcribe(audio_bytes, language=language)
    return {"data": {"text": text}}
