"""Enhanced camera capture service with advanced green screen keying"""
import cv2
import numpy as np
import threading
import time
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class CameraConfig:
    """Camera configuration"""
    camera_id: int = 0
    width: int = 1080
    height: int = 1920
    fps: int = 25
    use_green_screen: bool = False
    
    # Green screen settings (学习相芯科技的抠图优化)
    green_lower_h: int = 35
    green_upper_h: int = 77
    green_lower_s: int = 43
    green_upper_s: int = 255
    green_lower_v: int = 46
    green_upper_v: int = 255
    
    # Edge refinement (边缘优化)
    edge_feather: int = 3
    edge_smooth: int = 5
    
    # Spill suppression (溢色抑制)
    spill_suppression: bool = True


class EnhancedCameraCapture:
    """
    增强版摄像头采集服务
    
    学习自相芯科技的模型优化经验：
    - 自适应绿幕抠图
    - 边缘优化
    - 溢色抑制
    - 帧缓存
    """
    
    def __init__(self, config: Optional[CameraConfig] = None):
        self.config = config or CameraConfig()
        
        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        
        # Frame buffer (帧缓存，防止卡顿)
        self._frame_buffer: list = []
        self._buffer_size = 3
        
        # Green screen kernel
        self._kernel = np.ones((self.config.edge_smooth, self.config.edge_smooth), np.uint8)
    
    def start(self) -> bool:
        """Start camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.config.camera_id)
            
            if not self.cap.isOpened():
                print(f"Error: Cannot open camera {self.config.camera_id}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Set exposure for better green screen keying
            self.cap.set(cv2.CAP_PROP_EXPOSURE, -5)
            
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            
            # Wait for first frame
            time.sleep(1.5)
            
            print(f"Camera started: {self.config.width}x{self.config.height} @ {self.config.fps}fps")
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def stop(self):
        """Stop camera capture"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("Camera stopped")
    
    def _capture_loop(self):
        """Background thread for capturing frames"""
        while self._running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if not ret:
                time.sleep(0.01)
                continue
            
            # Process frame
            if self.config.use_green_screen:
                frame = self._advanced_keying(frame)
            else:
                frame = cv2.resize(frame, (self.config.width, self.config.height))
            
            # Update frame buffer
            with self._frame_lock:
                if len(self._frame_buffer) >= self._buffer_size:
                    self._frame_buffer.pop(0)
                self._frame_buffer.append(frame.copy())
                self._latest_frame = self._frame_buffer[-1]
    
    def _advanced_keying(self, frame: np.ndarray) -> np.ndarray:
        """
        高级绿幕抠图（学习相芯科技优化经验）
        
        流程：
        1. HSV 颜色分割
        2. 形态学优化
        3. 边缘羽化
        4. 溢色抑制
        """
        # Resize to target dimensions
        frame = cv2.resize(frame, (self.config.width, self.config.height))
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define green range
        lower_green = np.array([
            self.config.green_lower_h,
            self.config.green_lower_s,
            self.config.green_lower_v
        ])
        upper_green = np.array([
            self.config.green_upper_h,
            self.config.green_upper_s,
            self.config.green_upper_v
        ])
        
        # Create initial mask
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Invert mask (we want to keep the person, remove green)
        mask = cv2.bitwise_not(mask)
        
        # Morphological operations for clean mask
        mask = cv2.erode(mask, self._kernel, iterations=2)
        mask = cv2.dilate(mask, self._kernel, iterations=2)
        
        # Edge feathering (边缘羽化)
        if self.config.edge_feather > 0:
            mask = cv2.GaussianBlur(mask, (self.config.edge_feather * 2 + 1, self.config.edge_feather * 2 + 1), 0)
        
        # Spill suppression (溢色抑制 - 去除人物边缘的绿色反光)
        if self.config.spill_suppression:
            frame = self._suppress_spill(frame, hsv)
        
        # Apply mask to frame
        result = cv2.bitwise_and(frame, frame, mask=mask)
        
        # Set background to black (will be replaced later)
        result[mask == 0] = [0, 0, 0]
        
        return result
    
    def _suppress_spill(self, frame: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        """抑制绿色溢出（人物边缘的绿色反光）"""
        # Find areas near green color
        green_mask = cv2.inRange(hsv, 
            np.array([35, 50, 50]),
            np.array([70, 255, 255])
        )
        
        # Dilate to find edges
        green_mask = cv2.dilate(green_mask, np.ones((5, 5), np.uint8), iterations=2)
        
        # Replace green tint with neutral color
        for c in range(3):
            channel = frame[:, :, c].astype(np.float32)
            # Reduce green influence
            frame[:, :, c] = np.where(
                green_mask > 0,
                channel * 0.7,  # Reduce green
                channel
            ).astype(np.uint8)
        
        return frame
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame"""
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None
    
    def get_frames(self, count: int = 1) -> list:
        """Get multiple frames from buffer"""
        with self._frame_lock:
            if count >= len(self._frame_buffer):
                return self._frame_buffer.copy()
            return self._frame_buffer[-count:].copy()
    
    def is_running(self) -> bool:
        """Check if camera is running"""
        return self._running and self.cap is not None and self.cap.isOpened()


# Quick test
if __name__ == "__main__":
    print("=== Enhanced Camera Capture Test ===")
    
    config = CameraConfig(
        camera_id=0,
        use_green_screen=False
    )
    
    camera = EnhancedCameraCapture(config)
    
    if camera.start():
        print("Press Ctrl+C to stop...")
        try:
            while True:
                frame = camera.get_frame()
                if frame is not None:
                    print(f"Frame received: {frame.shape}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            camera.stop()
