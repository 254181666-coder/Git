"""
防平台检测模块
"""
import random
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class AntiDetectService:
    def __init__(self):
        self.enable_random_pause = True
        self.enable_frame_jitter = True
        self.enable_bitrate_fluctuation = True
        self.min_random_pause = 0.5
        self.max_random_pause = 5.0
        self.pause_probability = 0.15
        
    def random_pause(self) -> float:
        """随机暂停，模拟真人看评论思考"""
        if not self.enable_random_pause:
            return 0.0
        if random.random() < self.pause_probability:
            pause = random.uniform(self.min_random_pause, self.max_random_pause)
            logger.debug(f"防检测随机暂停: {pause:.2f}s")
            return pause
        return 0.0
        
    def frame_jitter(self, base_fps: float) -> float:
        """FPS抖动"""
        if not self.enable_frame_jitter:
            return base_fps
        jitter = random.uniform(-1.0, 2.0)
        return max(25, min(30, base_fps + jitter))
        
    def bitrate_fluctuation(self, base_bitrate: int) -> int:
        """码率波动"""
        if not self.enable_bitrate_fluctuation:
            return base_bitrate
        fluctuation = int(base_bitrate * random.uniform(-0.1, 0.15))
        return max(2000, min(6000, base_bitrate + fluctuation))
        
    def speech_speed_vary(self, base_speed: float) -> float:
        """语速变化"""
        return base_speed * random.uniform(0.92, 1.08)
        
    def random_restart(self, current_runtime: float, avg_interval: float) -> bool:
        """随机重启推流连接"""
        if current_runtime > avg_interval:
            if random.random() < 0.1:
                logger.info("触发防检测随机重启")
                return True
        return False
        
    def get_improved_rtmp_args(self, base_url: str) -> Tuple[str, str]:
        """优化后的RTMP推流参数"""
        extra_args = " -flvflags no_duration_filesize"
        return base_url, extra_args

# 全局单例
anti_detect = AntiDetectService()