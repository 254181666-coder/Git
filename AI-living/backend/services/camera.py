"""Camera capture service for live streaming"""
import cv2
import numpy as np
import threading
import time
from typing import Optional, Tuple


class CameraCapture:
    """Camera capture with real-time processing"""
    
    def __init__(
        self,
        camera_id: int = 0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 25,
        use_green_screen: bool = False
    ):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.use_green_screen = use_green_screen
        
        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        
        # Green screen parameters
        self.lower_green = np.array([35, 43, 46])
        self.upper_green = np.array([77, 255, 255])
        
    def start(self) -> bool:
        """Start camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.cap.isOpened():
                print(f"Error: Cannot open camera {self.camera_id}")
                return False
            
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            
            # Wait for first frame
            time.sleep(1)
            
            print(f"Camera started: {self.width}x{self.height} @ {self.fps}fps")
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
            if self.use_green_screen:
                frame = self._remove_green_screen(frame)
            else:
                # Resize to target dimensions
                frame = cv2.resize(frame, (self.width, self.height))
            
            # Update latest frame
            with self._frame_lock:
                self._latest_frame = frame.copy()
    
    def _remove_green_screen(self, frame: np.ndarray) -> np.ndarray:
        """Remove green screen background"""
        # Resize to target dimensions
        frame = cv2.resize(frame, (self.width, self.height))
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        mask = cv2.bitwise_not(mask)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Apply mask to frame
        result = cv2.bitwise_and(frame, frame, mask=mask)
        
        return result
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame"""
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None
    
    def is_running(self) -> bool:
        """Check if camera is running"""
        return self._running and self.cap is not None and self.cap.isOpened()
