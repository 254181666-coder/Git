"""Enhanced streaming manager with monitoring and auto-recovery"""
import os
import logging
import subprocess
import threading
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Stream configuration"""
    rtmp_url: str
    width: int = 1080
    height: int = 1920
    fps: int = 25
    bitrate: int = 3000
    audio_bitrate: int = 128
    preset: str = "ultrafast"
    keyint: int = 25


@dataclass
class StreamStats:
    """Stream statistics for monitoring"""
    total_frames: int = 0
    dropped_frames: int = 0
    start_time: Optional[datetime] = None
    last_error: Optional[str] = None
    reconnect_count: int = 0
    uptime_seconds: float = 0.0


class EnhancedStreamingService:
    """
    增强版推流服务
    
    学习自硅基智能的稳定性设计：
    - 自动重连机制
    - 帧率监控
    - 错误恢复
    - 性能统计
    """
    
    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats = StreamStats()
        self._stats_lock = threading.Lock()
        self._frame_pipe: Optional = None
        
        # 重连配置（学习硅基智能）
        self._max_reconnects = 10
        self._reconnect_delay = 3
        self._reconnect_backoff = True
        
        # 帧率监控
        self._expected_fps = 25
        self._fps_tolerance = 0.2  # 允许20%误差
        
    def start(self, config: StreamConfig) -> bool:
        """启动推流"""
        if self._running:
            logger.warning("推流已在运行中")
            return False
        
        self.config = config
        self._running = True
        self._stats = StreamStats(start_time=datetime.now())
        self._stats.reconnect_count = 0
        
        success = self._launch_ffmpeg()
        if success:
            self._start_monitoring()
            logger.info(f"推流已启动: {config.rtmp_url}")
        return success
    
    def _launch_ffmpeg(self) -> bool:
        """启动FFmpeg进程"""
        if not self.config:
            return False
        
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self.config.width}x{self.config.height}",
            "-r", str(self.config.fps),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-preset", self.config.preset,
            "-tune", "zerolatency",
            "-b:v", f"{self.config.bitrate}k",
            "-pix_fmt", "yuv420p",
            "-g", str(self.config.keyint),
            "-keyint_min", str(self.config.keyint),
            "-sc_threshold", "0",
            "-f", "flv",
            self.config.rtmp_url
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            logger.error(f"FFmpeg启动失败: {e}")
            self._stats.last_error = str(e)
            return False
    
    def _start_monitoring(self):
        """启动监控线程"""
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_loop(self):
        """监控推流状态"""
        while self._running:
            if self.process:
                returncode = self.process.poll()
                if returncode is not None:
                    logger.warning(f"推流进程退出，返回码: {returncode}")
                    self._handle_disconnect()
                    continue
            
            # 检查帧率
            with self._stats_lock:
                if self._stats.total_frames > 0:
                    elapsed = (datetime.now() - self._stats.start_time).total_seconds()
                    actual_fps = self._stats.total_frames / max(elapsed, 0.1)
                    expected = self._expected_fps
                    
                    if actual_fps < expected * (1 - self._fps_tolerance):
                        logger.warning(f"帧率过低: {actual_fps:.1f} < {expected * 0.8:.1f}")
            
            time.sleep(2)
    
    def _handle_disconnect(self):
        """处理断线重连"""
        if not self._running:
            return
        
        with self._stats_lock:
            if self._stats.reconnect_count >= self._max_reconnects:
                logger.error("达到最大重连次数，停止推流")
                self._running = False
                return
            
            delay = self._reconnect_delay
            if self._reconnect_backoff:
                delay *= (1 + self._stats.reconnect_count * 0.5)
            
            self._stats.reconnect_count += 1
            self._stats.last_error = f"连接断开，第{self._stats.reconnect_count}次重连"
        
        logger.info(f"等待 {delay:.1f} 秒后重连...")
        time.sleep(delay)
        
        if self._running:
            self._launch_ffmpeg()
    
    def write_frame(self, frame_bytes: bytes) -> bool:
        """写入视频帧"""
        if not self.process or not self.process.stdin:
            return False
        
        try:
            self.process.stdin.write(frame_bytes)
            with self._stats_lock:
                self._stats.total_frames += 1
            return True
        except Exception as e:
            logger.error(f"写入帧失败: {e}")
            with self._stats_lock:
                self._stats.dropped_frames += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取推流统计"""
        with self._stats_lock:
            stats = {
                "running": self._running,
                "total_frames": self._stats.total_frames,
                "dropped_frames": self._stats.dropped_frames,
                "drop_rate": self._stats.dropped_frames / max(self._stats.total_frames, 1) * 100,
                "reconnect_count": self._stats.reconnect_count,
                "last_error": self._stats.last_error,
                "uptime": (datetime.now() - self._stats.start_time).total_seconds() if self._stats.start_time else 0
            }
            
            if self._stats.total_frames > 0:
                elapsed = stats["uptime"]
                stats["actual_fps"] = self._stats.total_frames / max(elapsed, 0.1)
            
            return stats
    
    def stop(self):
        """停止推流"""
        self._running = False
        
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("推流已停止")
