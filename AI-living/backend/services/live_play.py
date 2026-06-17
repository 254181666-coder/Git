"""
直播玩法服务
"""
import cv2
import numpy as np
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class LivePlayService:
    def __init__(self):
        self.video_source = None
        self.is_streaming = False
        
    def remove_duplicate(self, frame: np.ndarray) -> np.ndarray:
        """画面去重处理"""
        noise = np.random.normal(0, 2, frame.shape).astype(np.uint8)
        return cv2.add(frame, noise)
        
    def get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%H:%M:%S")
        
    def load_video(self, video_path: str):
        """加载录播视频"""
        self.video_source = video_path
        logger.info(f"加载视频: {video_path}")
        
    def get_video_frame(self) -> Optional[np.ndarray]:
        """获取视频帧"""
        if self.video_source:
            cap = cv2.VideoCapture(self.video_source)
            ret, frame = cap.read()
            cap.release()
            if ret:
                return frame
        return None

# 全局单例
live_play = LivePlayService()