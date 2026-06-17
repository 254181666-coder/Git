"""
画面合成与实时预览API
"""
import cv2
import base64
import logging
import numpy as np
import json
import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import threading
import time

from services.compositor import chromakey, compositor, camera_state, OverlayConfig, OverlayType, BackgroundConfig

router = APIRouter()
logger = logging.getLogger(__name__)

class BackgroundRequest(BaseModel):
    type: str = "solid"
    source: Optional[str] = None
    color: Optional[List[int]] = None

class OverlayRequest(BaseModel):
    type: str
    source: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    opacity: float = 1.0
    z_index: int = 0

class ChromaKeyRequest(BaseModel):
    color: str = "green"
    hue_min: Optional[int] = None
    hue_max: Optional[int] = None
    sat_min: Optional[int] = None
    sat_max: Optional[int] = None

def _encode_jpeg(frame: np.ndarray) -> str:
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')

def _make_demo_foreground(width: int, height: int) -> np.ndarray:
    """Create a transparent demo foreground for no-camera previews."""
    foreground = np.zeros((height, width, 4), dtype=np.uint8)
    now = datetime.now().strftime("%H:%M:%S")

    center_x = width // 2
    body_top = int(height * 0.24)
    body_bottom = int(height * 0.74)
    head_radius = max(48, min(width, height) // 11)

    cv2.circle(foreground, (center_x, body_top), head_radius, (225, 232, 244, 255), -1)
    cv2.ellipse(
        foreground,
        (center_x, int(height * 0.50)),
        (int(width * 0.20), int(height * 0.20)),
        0,
        0,
        360,
        (65, 125, 220, 255),
        -1
    )
    cv2.rectangle(
        foreground,
        (int(width * 0.18), int(height * 0.78)),
        (int(width * 0.82), int(height * 0.86)),
        (255, 255, 255, 180),
        -1
    )

    cv2.putText(foreground, "AI-living Demo", (int(width * 0.10), int(height * 0.10)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255, 255), 3)
    cv2.putText(foreground, f"{width}x{height}  {now}", (int(width * 0.10), int(height * 0.15)), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (235, 245, 255, 255), 2)
    cv2.putText(foreground, "No camera required", (int(width * 0.10), int(height * 0.91)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255, 255), 2)

    return foreground

@router.post("/background")
async def set_background(req: BackgroundRequest):
    """设置背景"""
    config = BackgroundConfig(
        type=req.type,
        source=req.source,
        color=tuple(req.color) if req.color else None
    )
    compositor.set_background(config)
    return {"status": "ok", "message": "背景已设置"}

@router.post("/background/snack_room")
async def apply_snack_room_background():
    """应用零食直播间背景图。"""
    source = "data/backgrounds/snacks/snack_live_room_bg.png"
    if not os.path.exists(source):
        return {"status": "error", "message": "零食直播间背景图不存在"}
    compositor.set_background(BackgroundConfig(type="image", source=source))
    return {"status": "ok", "message": "零食直播间背景已应用", "source": source}

@router.post("/overlay")
async def add_overlay(req: OverlayRequest):
    """添加贴片"""
    overlay = OverlayConfig(
        type=OverlayType(req.type),
        source=req.source,
        x=req.x,
        y=req.y,
        width=req.width,
        height=req.height,
        opacity=req.opacity,
        z_index=req.z_index
    )
    compositor.add_overlay(overlay)
    return {"status": "ok", "message": "贴片已添加"}

@router.post("/overlay/remove")
async def remove_overlay(source: str):
    """移除贴片"""
    compositor.remove_overlay(source)
    return {"status": "ok", "message": "贴片已移除"}

@router.post("/overlay/clear")
async def clear_overlays():
    """清空所有贴片"""
    compositor.clear_overlays()
    return {"status": "ok", "message": "贴片已清空"}

@router.post("/overlay/snack_pack")
async def apply_snack_overlay_pack():
    """应用零食直播贴片包。"""
    pack_dir = "data/overlays/snacks"
    manifest_path = os.path.join(pack_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return {"status": "error", "message": "零食贴片包不存在"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    compositor.clear_overlays()
    for index, item in enumerate(manifest.get("items", [])):
        source = os.path.join(pack_dir, item["file"])
        if not os.path.exists(source):
            continue
        compositor.add_overlay(OverlayConfig(
            type=OverlayType.IMAGE,
            source=source,
            x=int(item.get("x", 0)),
            y=int(item.get("y", 0)),
            width=int(item.get("width", 0)),
            height=int(item.get("height", 0)),
            opacity=float(item.get("opacity", 1.0)),
            z_index=index
        ))

    return {
        "status": "ok",
        "message": "零食贴片包已应用",
        "count": len(compositor.overlays)
    }

@router.post("/chromakey")
async def set_chromakey(req: ChromaKeyRequest):
    """设置绿幕抠图参数"""
    chromakey.set_color_range(req.color)
    
    if req.hue_min is not None:
        chromakey.lower_green[0] = req.hue_min
    if req.hue_max is not None:
        chromakey.upper_green[0] = req.hue_max
    if req.sat_min is not None:
        chromakey.lower_green[1] = req.sat_min
    if req.sat_max is not None:
        chromakey.upper_green[1] = req.sat_max
    
    return {"status": "ok", "message": "抠图参数已设置"}

@router.get("/preview")
async def get_preview_frame():
    """获取当前预览帧"""
    frame = camera_state.last_frame
    
    if frame is not None:
        if camera_state.use_chroma_key:
            foreground, mask = chromakey.remove_background(frame)
        else:
            foreground, mask = frame, None
        
        # 合成画面
        result = compositor.composite(foreground)
        
        return {
            "frame": _encode_jpeg(result),
            "has_mask": mask is not None,
            "source": "camera",
            "camera_running": camera_state.is_running,
            "last_error": camera_state.last_error
        }

    demo_foreground = _make_demo_foreground(compositor.width, compositor.height)
    result = compositor.composite(demo_foreground)
    return {
        "frame": _encode_jpeg(result),
        "source": "demo",
        "has_mask": False,
        "camera_running": camera_state.is_running,
        "last_error": camera_state.last_error,
        "message": "演示画面已启用，无需摄像头"
    }

@router.post("/upload/background")
async def upload_background(file: UploadFile = File(...)):
    """上传背景图"""
    contents = await file.read()
    
    import os
    save_dir = "data/backgrounds"
    os.makedirs(save_dir, exist_ok=True)
    
    filepath = os.path.join(save_dir, file.filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    
    config = BackgroundConfig(type="image", source=filepath)
    compositor.set_background(config)
    
    return {"status": "ok", "filepath": filepath}

@router.post("/upload/overlay")
async def upload_overlay(
    file: UploadFile = File(...),
    x: int = Form(0),
    y: int = Form(0),
    width: int = Form(0),
    height: int = Form(0),
    z_index: int = Form(0)
):
    """上传贴片图片"""
    contents = await file.read()
    
    import os
    save_dir = "data/overlays"
    os.makedirs(save_dir, exist_ok=True)
    
    filepath = os.path.join(save_dir, file.filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    
    overlay = OverlayConfig(
        type=OverlayType.IMAGE,
        source=filepath,
        x=x,
        y=y,
        width=width,
        height=height,
        z_index=z_index
    )
    compositor.add_overlay(overlay)
    
    return {"status": "ok", "filepath": filepath}
