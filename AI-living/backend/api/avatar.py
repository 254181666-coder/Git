"""
数字人驱动API
"""
import cv2
import logging
import platform
from fastapi import APIRouter

from models.schemas import AvatarModeRequest, AvatarConfig, DriverMode

router = APIRouter()
logger = logging.getLogger(__name__)

class AvatarState:
    def __init__(self):
        self.mode = DriverMode.CAMERA
        self.cap = None
        self.is_running = False

avatar_state = AvatarState()

def _camera_backends():
    system = platform.system()
    if system == "Darwin":
        return [cv2.CAP_AVFOUNDATION]
    if system == "Windows":
        return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    return [cv2.CAP_ANY]

def _open_camera(camera_id: int):
    for backend in _camera_backends():
        cap = cv2.VideoCapture(camera_id, backend)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()
    return None

@router.post("/mode")
async def set_mode(req: AvatarModeRequest):
    """设置驱动模式"""
    avatar_state.mode = req.mode
    return {"status": "ok", "mode": req.mode.value}

@router.post("/camera/start")
async def start_camera(camera_id: int = 0):
    """开启摄像头"""
    avatar_state.cap = _open_camera(camera_id)
    avatar_state.is_running = avatar_state.cap is not None
    if not avatar_state.is_running:
        return {"status": "error", "message": "摄像头打开失败"}
    return {"status": "ok"}

@router.post("/camera/stop")
async def stop_camera():
    """关闭摄像头"""
    if avatar_state.cap:
        avatar_state.cap.release()
        avatar_state.cap = None
    avatar_state.is_running = False
    return {"status": "ok"}

@router.get("/status")
async def get_status():
    return {
        "mode": avatar_state.mode.value,
        "is_running": avatar_state.is_running
    }
