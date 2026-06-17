"""
真人直播模式 - 摄像头采集和推流
"""
import cv2
import logging
import platform
import threading
import time
import base64
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.streaming import streaming, StreamConfig
from services.ai_driver import ai_driver
from services.compositor import camera_state, compositor

router = APIRouter()
logger = logging.getLogger(__name__)

class LiveMode(BaseModel):
    mode: str = "real_person"  # real_person, ai, pip, alternate
    camera_id: Optional[int] = 0
    width: Optional[int] = 1080
    height: Optional[int] = 1920
    fps: Optional[int] = 30
    frame_fit: Optional[str] = "contain"  # contain, cover, stretch
    frame_rotation: Optional[str] = "none"  # none, rotate90, rotate180, rotate270
    use_chroma_key: Optional[bool] = False
    show_ai_tips: Optional[bool] = True
    pip_position: Optional[str] = "bottom_right"
    alternate_interval: Optional[int] = 300

def _camera_backends():
    system = platform.system()
    if system == "Darwin":
        return [("AVFOUNDATION", cv2.CAP_AVFOUNDATION)]
    if system == "Windows":
        return [("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF), ("ANY", cv2.CAP_ANY)]
    return [("ANY", cv2.CAP_ANY)]

def _open_camera(camera_id, width=None, height=None, fps=None):
    last_backend = ""
    for backend_name, backend in _camera_backends():
        last_backend = backend_name
        cap = cv2.VideoCapture(camera_id, backend)
        if not cap.isOpened():
            cap.release()
            continue
        if width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps:
            cap.set(cv2.CAP_PROP_FPS, fps)
        ok, _ = cap.read()
        if ok:
            return cap, backend_name
        cap.release()
    return None, last_backend

def _rotate_frame(frame, rotation):
    if rotation == "rotate90":
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if rotation == "rotate180":
        return cv2.rotate(frame, cv2.ROTATE_180)
    if rotation == "rotate270":
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame

def _camera_loop(camera_id, width, height, fps, rotation):
    """摄像头采集线程"""
    cap, backend_name = _open_camera(camera_id, width, height, fps)
    if not cap:
        logger.error("摄像头打开失败")
        camera_state.last_error = f"摄像头 {camera_id} 打开失败"
        camera_state.is_running = False
        return

    camera_state.cap = cap
    camera_state.last_error = ""
    logger.info(f"摄像头已打开: id={camera_id}, backend={backend_name}")
    
    while camera_state.is_running:
        ret, frame = cap.read()
        if ret:
            camera_state.last_frame = _rotate_frame(frame, rotation)
            camera_state.frame_count += 1
        else:
            camera_state.last_error = "摄像头读取画面失败"
            break
        time.sleep(1.0 / max(fps, 1))
        
    cap.release()
    camera_state.cap = None

@router.post("/start")
async def start_live_mode(req: LiveMode):
    """启动真人直播模式"""
    camera_state.current_mode = req.mode
    camera_state.ai_tip_visible = bool(req.show_ai_tips)
    camera_state.camera_id = req.camera_id or 0
    camera_state.use_chroma_key = bool(req.use_chroma_key)
    camera_state.frame_fit = req.frame_fit or "contain"
    camera_state.frame_rotation = req.frame_rotation or "none"
    camera_state.frame_count = 0
    compositor.set_resolution(req.width or 1080, req.height or 1920)
    compositor.set_foreground_fit(camera_state.frame_fit)
    
    if req.mode == "real_person":
        # 真人出镜模式
        if not camera_state.is_running:
            camera_state.is_running = True
            camera_state._thread = threading.Thread(
                target=_camera_loop,
                args=(
                    req.camera_id or 0,
                    req.width or 1080,
                    req.height or 1920,
                    req.fps or 30,
                    camera_state.frame_rotation
                ),
                daemon=True
            )
            camera_state._thread.start()
            time.sleep(0.5)
            if not camera_state.is_running:
                return {"status": "error", "message": camera_state.last_error or "摄像头启动失败"}
            logger.info("摄像头已启动，真人出镜模式")
        return {"status": "ok", "mode": "real_person"}
        
    elif req.mode == "pip":
        # 画中画模式：AI主画面+真人小窗
        return {"status": "ok", "mode": "pip", "message": "画中画模式已启动"}
        
    elif req.mode == "alternate":
        # 交替模式：真人和AI交替出镜
        camera_state.is_running = True
        camera_state._thread = threading.Thread(
            target=_camera_loop,
            args=(
                req.camera_id or 0,
                req.width or 1080,
                req.height or 1920,
                req.fps or 30,
                camera_state.frame_rotation
            ),
            daemon=True
        )
        camera_state._thread.start()
        time.sleep(0.5)
        if not camera_state.is_running:
            return {"status": "error", "message": camera_state.last_error or "摄像头启动失败"}
        return {"status": "ok", "mode": "alternate", "interval": req.alternate_interval}
        
    return {"status": "error", "message": "不支持的模式"}

@router.post("/stop")
async def stop_live_mode():
    """停止真人直播模式"""
    camera_state.is_running = False
    if camera_state._thread:
        camera_state._thread.join(timeout=3)
        camera_state._thread = None
    return {"status": "ok"}

@router.get("/frame")
async def get_camera_frame():
    """获取当前摄像头帧（用于前端预览）"""
    if camera_state.last_frame is not None:
        _, buffer = cv2.imencode('.jpg', camera_state.last_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return {"frame": frame_base64}
    return {"frame": None}

@router.get("/status")
async def get_live_mode_status():
    """获取当前直播模式状态"""
    return {
        "mode": camera_state.current_mode,
        "camera_running": camera_state.is_running,
        "camera_id": camera_state.camera_id,
        "use_chroma_key": camera_state.use_chroma_key,
        "frame_fit": camera_state.frame_fit,
        "frame_rotation": camera_state.frame_rotation,
        "frame_count": camera_state.frame_count,
        "last_error": camera_state.last_error,
        "ai_tip_visible": camera_state.ai_tip_visible
    }

@router.post("/capture")
async def capture_face(camera_id: Optional[int] = 0):
    """采集人脸照片"""
    cap, _ = _open_camera(camera_id)
    if not cap:
        return {"status": "error", "message": "摄像头打开失败"}
        
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        import os
        save_dir = "data/faces"
        os.makedirs(save_dir, exist_ok=True)
        import time
        filename = f"face_{int(time.time())}.jpg"
        filepath = os.path.join(save_dir, filename)
        cv2.imwrite(filepath, frame)
        return {"status": "ok", "filepath": filepath, "filename": filename}
    else:
        return {"status": "error", "message": "采集失败"}

@router.post("/ai_tip")
async def update_ai_tip(tip: str):
    """更新AI提示文字"""
    camera_state.current_ai_tip = tip
    return {"status": "ok"}
