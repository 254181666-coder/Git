"""
直播管理API
"""
import logging
from datetime import datetime
from fastapi import APIRouter

from services.streaming import streaming, StreamConfig
from services.scheduler import scheduler
from services.ai_driver import ai_driver
from services.compositor import compositor
from models.schemas import StreamStartRequest, StatusResponse, ScriptItem

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/start")
async def start_stream(req: StreamStartRequest):
    """启动推流"""
    config = StreamConfig(
        rtmp_url=req.rtmp_url,
        width=req.width or 1080,
        height=req.height or 1920,
        fps=req.fps or 30,
        bitrate=req.bitrate or 4000,
        enable_audio=req.enable_audio if req.enable_audio is not None else True,
        audio_bitrate=req.audio_bitrate or 128,
        audio_file=req.audio_file,
        enable_anti_detect=req.enable_anti_detect if req.enable_anti_detect is not None else True,
        dry_run=bool(req.dry_run)
    )
    compositor.set_resolution(config.width, config.height)
    
    success = streaming.start_stream(config)
    if success:
        message = "本地演示推流已启动" if config.dry_run else "推流启动成功"
        return {"status": "ok", "message": message, "dry_run": config.dry_run}
    return {"status": "error", "message": "推流启动失败"}

@router.post("/stop")
async def stop_stream():
    """停止推流"""
    if scheduler.is_running():
        scheduler.stop()
    streaming.stop_stream()
    return {"status": "ok", "message": "推流已停止"}

@router.post("/schedule/start")
async def start_schedule(driver: str = "openai"):
    """启动话术轮播"""
    if not streaming.is_running():
        return {"status": "error", "message": "推流未启动"}
    if not ai_driver.is_connected(driver):
        return {"status": "error", "message": "AI服务未连接"}
    success = scheduler.start(driver)
    if success:
        return {"status": "ok", "message": "轮播启动成功"}
    return {"status": "error", "message": "轮播启动失败"}

@router.post("/schedule/stop")
async def stop_schedule():
    scheduler.stop()
    return {"status": "ok", "message": "轮播已停止"}

@router.get("/status")
async def get_status():
    """获取直播状态"""
    current = scheduler.get_current_script()
    return {
        "is_streaming": streaming.is_running(),
        "dry_run": streaming.is_dry_run(),
        "runtime_seconds": streaming.uptime_seconds(),
        "is_scheduling": scheduler.is_running(),
        "current_script": current.dict() if current else None,
        "ai_connected": ai_driver.is_connected(),
        "audio_enabled": bool(streaming.config and streaming.config.enable_audio),
        "audio_file": streaming.config.audio_file if streaming.config else None
    }

@router.get("/timestamp")
async def get_timestamp():
    """获取当前时间戳，兼容直播玩法页面。"""
    return {
        "status": "ok",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
