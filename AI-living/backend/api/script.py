"""
话术管理API
"""
import uuid
import logging
from fastapi import APIRouter

from services.scheduler import scheduler, ScriptItem
from models.schemas import ScriptCreate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/add")
async def add_script(req: ScriptCreate):
    """添加话术"""
    script = ScriptItem(
        id=str(uuid.uuid4()),
        text=req.text,
        face_id=req.face_id,
        voice_id=req.voice_id,
        duration=req.duration or 0.0,
        priority=req.priority or 0
    )
    scheduler.add_script(script)
    return {"status": "ok", "script_id": script.id}

@router.post("/clear")
async def clear_scripts():
    scheduler.clear_scripts()
    return {"status": "ok"}

@router.get("/list")
async def list_scripts():
    return {
        "count": len(scheduler.scripts),
        "scripts": [s.dict() for s in scheduler.scripts]
    }