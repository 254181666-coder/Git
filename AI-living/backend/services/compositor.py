"""
绿幕抠图与画面合成服务
"""
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OverlayType(str, Enum):
    IMAGE = "image"      # 图片贴片
    TEXT = "text"        # 文字贴片
    WATERMARK = "watermark"  # 水印

@dataclass
class OverlayConfig:
    """贴片配置"""
    type: OverlayType
    source: str          # 图片路径或文字内容
    x: int = 0           # X位置
    y: int = 0           # Y位置
    width: int = 0       # 宽度
    height: int = 0      # 高度
    opacity: float = 1.0 # 透明度
    z_index: int = 0     # 层级

@dataclass
class BackgroundConfig:
    """背景配置"""
    type: str = "solid"  # solid, image, video
    source: Optional[str] = None
    color: Tuple[int, int, int] = (0, 0, 0)

class CameraState:
    """摄像头状态"""
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.current_mode = "real_person"
        self.last_frame = None
        self._thread = None
        self.camera_id = 0
        self.use_chroma_key = False
        self.frame_count = 0
        self.last_error = ""
        self.ai_tip_visible = True
        self.current_ai_tip = ""
        self.frame_fit = "contain"
        self.frame_rotation = "none"

class ChromaKeyService:
    """绿幕抠图服务"""
    
    def __init__(self):
        # 默认绿幕颜色范围（HSV）
        self.lower_green = np.array([35, 43, 46])
        self.upper_green = np.array([77, 255, 255])
        
        # 可调整的参数
        self.hue_min = 35
        self.hue_max = 77
        self.sat_min = 43
        self.sat_max = 255
        self.val_min = 46
        self.val_max = 255
    
    def set_color_range(self, color: str = "green"):
        """设置抠图颜色范围"""
        if color == "green":
            self.lower_green = np.array([35, 43, 46])
            self.upper_green = np.array([77, 255, 255])
        elif color == "blue":
            self.lower_green = np.array([100, 43, 46])
            self.upper_green = np.array([130, 255, 255])
        elif color == "red":
            self.lower_green = np.array([0, 43, 46])
            self.upper_green = np.array([15, 255, 255])
    
    def remove_background(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        绿幕抠图
        返回：抠图后的画面，掩码
        """
        if frame is None:
            return None, None
        
        # 转换到HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 创建掩码
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        mask = cv2.bitwise_not(mask)
        
        # 优化掩码（去除噪点）
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # 抠出前景，并把掩码写成 Alpha 通道，方便后续真实背景合成。
        result = cv2.bitwise_and(frame, frame, mask=mask)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
        result[:, :, 3] = mask
        
        return result, mask
    
    def remove_background_ai(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        AI智能抠图（无需绿幕）
        需要安装: pip install rembg
        """
        try:
            from rembg import remove
            from PIL import Image
            
            input_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            output_image = remove(input_image)
            return cv2.cvtColor(np.array(output_image), cv2.COLOR_RGB2BGR)
        except ImportError:
            logger.warning("rembg未安装，使用绿幕抠图")
            result, _ = self.remove_background(frame)
            return result

# 全局单例
chromakey = ChromaKeyService()
# 全局摄像头状态（供API共享）
camera_state = CameraState()


class CompositorService:
    """画面合成服务"""
    
    def __init__(self):
        self.background: Optional[BackgroundConfig] = BackgroundConfig()
        self.overlays: List[OverlayConfig] = []
        self.width = 1080
        self.height = 1920
        self.foreground_fit = "contain"
    
    def set_resolution(self, width: int, height: int):
        self.width = width
        self.height = height

    def set_foreground_fit(self, fit: str):
        if fit in {"contain", "cover", "stretch"}:
            self.foreground_fit = fit
    
    def set_background(self, config: BackgroundConfig):
        self.background = config
    
    def add_overlay(self, config: OverlayConfig):
        self.overlays.append(config)
        self.overlays.sort(key=lambda x: x.z_index)
    
    def remove_overlay(self, overlay_id: str):
        self.overlays = [o for o in self.overlays if o.source != overlay_id]
    
    def clear_overlays(self):
        self.overlays.clear()
    
    def composite(self, foreground: Optional[np.ndarray] = None) -> np.ndarray:
        """
        合成画面
        流程：背景 → 前景（抠图后） → 贴片
        """
        # 创建背景
        canvas = self._create_background()
        
        # 叠加前景（人物）
        if foreground is not None:
            canvas = self._blend_foreground(canvas, foreground)
        
        # 叠加贴片
        for overlay in self.overlays:
            canvas = self._apply_overlay(canvas, overlay)
        
        return canvas
    
    def _create_background(self) -> np.ndarray:
        """创建背景层"""
        if self.background.type == "solid":
            color = self.background.color or (0, 0, 0)
            return np.full((self.height, self.width, 3), color, dtype=np.uint8)
        
        elif self.background.type == "image" and self.background.source:
            bg = cv2.imread(self.background.source)
            if bg is not None:
                return cv2.resize(bg, (self.width, self.height))
        
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
    
    def _blend_foreground(self, canvas: np.ndarray, foreground: np.ndarray) -> np.ndarray:
        """叠加前景（支持透明通道）"""
        if foreground is None:
            return canvas
        
        fg = self._fit_to_canvas(foreground)
        
        # 如果有Alpha通道，进行混合
        if fg.shape[2] == 4:
            alpha = fg[:, :, 3] / 255.0
            alpha = np.stack([alpha] * 3, axis=2)
            canvas = (canvas * (1 - alpha) + fg[:, :, :3] * alpha).astype(np.uint8)
        else:
            # 无Alpha通道，直接覆盖（居中）
            h, w = fg.shape[:2]
            y_offset = (self.height - h) // 2
            x_offset = (self.width - w) // 2
            
            canvas[y_offset:y_offset+h, x_offset:x_offset+w] = fg
        
        return canvas

    def _fit_to_canvas(self, foreground: np.ndarray) -> np.ndarray:
        """按配置将前景适配到画布，避免横竖屏直接拉伸变形。"""
        if self.foreground_fit == "stretch":
            return cv2.resize(foreground, (self.width, self.height))

        src_h, src_w = foreground.shape[:2]
        if src_w <= 0 or src_h <= 0:
            return cv2.resize(foreground, (self.width, self.height))

        scale_x = self.width / src_w
        scale_y = self.height / src_h
        scale = max(scale_x, scale_y) if self.foreground_fit == "cover" else min(scale_x, scale_y)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = cv2.resize(foreground, (new_w, new_h))

        if self.foreground_fit == "cover":
            x = max(0, (new_w - self.width) // 2)
            y = max(0, (new_h - self.height) // 2)
            return resized[y:y + self.height, x:x + self.width]

        channels = resized.shape[2] if len(resized.shape) == 3 else 1
        canvas_shape = (self.height, self.width, channels) if channels > 1 else (self.height, self.width)
        fitted = np.zeros(canvas_shape, dtype=resized.dtype)
        x = max(0, (self.width - new_w) // 2)
        y = max(0, (self.height - new_h) // 2)
        fitted[y:y + new_h, x:x + new_w] = resized
        return fitted
    
    def _apply_overlay(self, canvas: np.ndarray, overlay: OverlayConfig) -> np.ndarray:
        """应用贴片"""
        if overlay.type == OverlayType.IMAGE and overlay.source:
            img = cv2.imread(overlay.source)
            if img is not None:
                if overlay.width > 0 and overlay.height > 0:
                    img = cv2.resize(img, (overlay.width, overlay.height))
                
                h, w = img.shape[:2]
                y1, y2 = overlay.y, overlay.y + h
                x1, x2 = overlay.x, overlay.x + w
                
                # 边界检查
                y1 = max(0, min(y1, self.height))
                y2 = max(0, min(y2, self.height))
                x1 = max(0, min(x1, self.width))
                x2 = max(0, min(x2, self.width))
                
                if y2 > y1 and x2 > x1:
                    if img.shape[2] == 4:
                        # 有透明通道
                        alpha = img[:, :, 3] / 255.0
                        for c in range(3):
                            canvas[y1:y2, x1:x2, c] = \
                                (canvas[y1:y2, x1:x2, c] * (1 - alpha) + 
                                 img[:, :, c] * alpha).astype(np.uint8)
                    else:
                        canvas[y1:y2, x1:x2] = img
        
        elif overlay.type == OverlayType.TEXT:
            cv2.putText(
                canvas,
                overlay.source,
                (overlay.x, overlay.y),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2
            )
        
        return canvas

# 全局单例
compositor = CompositorService()
