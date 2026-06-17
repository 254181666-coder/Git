"""
话术轮播调度服务
"""
import logging
import random
import threading
import time
from typing import List, Optional
from dataclasses import dataclass

from .ai_driver import ai_driver
from .streaming import streaming
from .anti_detect import anti_detect

logger = logging.getLogger(__name__)

@dataclass
class ScriptItem:
    id: str
    text: str
    face_id: Optional[str] = None
    voice_id: Optional[str] = None
    duration: float = 0.0
    priority: int = 0

class ScheduleService:
    def __init__(self):
        self.scripts: List[ScriptItem] = []
        self.current_index: int = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.paused = False
        self.ai_driver_type = "openai"
        
    def add_script(self, script: ScriptItem):
        self.scripts.append(script)
        
    def clear_scripts(self):
        self.scripts.clear()
        self.current_index = 0
        
    def start(self, ai_driver_type: str = "openai"):
        """启动轮播"""
        if len(self.scripts) == 0:
            logger.error("话术列表为空")
            return False
        if self._running:
            logger.warning("轮播已经在运行")
            return False
            
        self._running = True
        self.ai_driver_type = ai_driver_type
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"轮播启动，共 {len(self.scripts)} 条话术")
        return True
        
    def stop(self):
        """停止轮播"""
        self._running = False
        self.paused = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("轮播已停止")
        
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def _run_loop(self):
        """轮播主循环"""
        while self._running:
            if self.paused:
                time.sleep(1)
                continue
                
            if not streaming.is_running():
                logger.error("推流未运行，停止轮播")
                self._running = False
                break
                
            current = self.scripts[self.current_index]
            logger.info(f"播放话术 {self.current_index + 1}/{len(self.scripts)}")
            
            # 防检测随机暂停
            delay = anti_detect.random_pause()
            if delay > 0:
                time.sleep(delay)
            
            # AI生成回复
            response = ai_driver.generate_response(current.text)
            
            # 等待播放完成
            duration = current.duration if current.duration > 0 else len(response) / 4.0
            duration += random.uniform(-0.5, 1.5)
            time.sleep(duration)
            
            self._next_script()
            
    def _next_script(self):
        self.current_index = (self.current_index + 1) % len(self.scripts)
        
    def is_running(self) -> bool:
        return self._running
        
    def get_current_script(self) -> Optional[ScriptItem]:
        if 0 <= self.current_index < len(self.scripts):
            return self.scripts[self.current_index]
        return None

# 全局单例
scheduler = ScheduleService()