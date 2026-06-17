"""
TTS语音合成API
"""
import logging
from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional

from services.tts import tts_service, TTSEngine

router = APIRouter()
logger = logging.getLogger(__name__)

class TTSSynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = ""
    engine: Optional[str] = "system"

class TTSEngineRequest(BaseModel):
    engine: str

@router.post("/synthesize")
async def synthesize_speech(req: TTSSynthesizeRequest):
    """合成语音"""
    try:
        engine = TTSEngine(req.engine) if req.engine else tts_service.current_engine
        tts_service.set_engine(engine)
        
        audio_data, error = tts_service.synthesize(req.text, req.voice_id)
        
        if error:
            return {"status": "error", "message": error}
        
        return {
            "status": "ok",
            "audio_size": len(audio_data) if audio_data else 0,
            "content_type": "audio/wav",
            "engine": engine.value
        }
    except Exception as e:
        logger.error(f"TTS合成失败: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/synthesize/audio")
async def synthesize_audio(req: TTSSynthesizeRequest):
    """合成语音并直接返回WAV音频。"""
    try:
        engine = TTSEngine(req.engine) if req.engine else tts_service.current_engine
        tts_service.set_engine(engine)
        audio_data, error = tts_service.synthesize(req.text, req.voice_id)

        if error:
            return Response(content=error, status_code=400, media_type="text/plain; charset=utf-8")

        return Response(content=audio_data or b"", media_type="audio/wav")
    except Exception as e:
        logger.error(f"TTS音频返回失败: {str(e)}")
        return Response(content=str(e), status_code=500, media_type="text/plain; charset=utf-8")

@router.post("/set_engine")
async def set_tts_engine(req: TTSEngineRequest):
    """切换TTS引擎"""
    try:
        engine = TTSEngine(req.engine)
        tts_service.set_engine(engine)
        return {"status": "ok", "engine": engine.value}
    except ValueError:
        return {"status": "error", "message": f"不支持的引擎: {req.engine}"}

@router.get("/voices")
async def list_voices():
    """列出可用音色"""
    voices = tts_service.list_voices()
    return {
        "status": "ok",
        "voices": voices,
        "current_engine": tts_service.current_engine.value
    }

@router.get("/status")
async def get_tts_status():
    """获取TTS状态"""
    return {
        "status": "ok",
        "available": tts_service.is_available(),
        "current_engine": tts_service.current_engine.value,
        "available_engines": list(tts_service.engines.keys())
    }
