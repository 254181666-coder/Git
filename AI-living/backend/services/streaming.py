"""
RTMP推流服务 - 优化版
"""
import os
import logging
import subprocess
import threading
import time
import shlex
from typing import Optional
from dataclasses import dataclass
import cv2
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class StreamConfig:
    rtmp_url: str
    width: int = 1080
    height: int = 1920
    fps: int = 30
    bitrate: int = 4000
    enable_audio: bool = True
    audio_bitrate: int = 128
    audio_file: Optional[str] = None
    enable_anti_detect: bool = True
    dry_run: bool = False

class StreamingService:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.config: Optional[StreamConfig] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_thread: Optional[threading.Thread] = None
        self._restart_count = 0
        self._max_restarts = 5
        self._started_at: Optional[float] = None
        
    def start_stream(self, config: StreamConfig) -> bool:
        """启动RTMP推流"""
        if self._running:
            logger.warning("推流已经在运行中")
            return False
            
        self.config = config
        self._running = True
        self._restart_count = 0
        self._started_at = time.time()

        if config.dry_run:
            logger.info("本地演示推流已启动，不连接RTMP或FFmpeg")
            return True
        
        return self._start_ffmpeg()

    def _start_ffmpeg(self) -> bool:
        """启动FFmpeg进程"""
        if not self.config:
            return False
            
        rtmp_url = self.config.rtmp_url
        
        audio_input = []
        audio_output = []
        if self.config.enable_audio:
            if self.config.audio_file and os.path.exists(self.config.audio_file):
                audio_input = ["-stream_loop", "-1", "-i", self.config.audio_file]
            else:
                audio_input = [
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            audio_output = [
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:a",
                "aac",
                "-b:a",
                f"{self.config.audio_bitrate}k",
                "-ar",
                "44100",
                "-ac",
                "2",
            ]
        else:
            audio_output = ["-map", "0:v:0", "-an"]

        # FFmpeg推流参数
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.config.width}x{self.config.height}",
            "-r", str(self.config.fps),
            "-i", "pipe:0",
            *audio_input,
            "-c:v", "libx264",
            "-preset", "veryfast",    # 编码速度
            "-b:v", f"{self.config.bitrate}k",
            "-maxrate", f"{int(self.config.bitrate * 1.5)}k",
            "-bufsize", f"{int(self.config.bitrate * 2)}k",
            "-pix_fmt", "yuv420p",
            "-g", str(self.config.fps * 2),  # 关键帧间隔
            "-sc_threshold", "0",     # 关闭场景切换
            *audio_output,
            "-f", "flv",
            "-flvflags", "no_duration_filesize",
            rtmp_url
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"推流进程启动成功: {rtmp_url[:50]}...")
            self._restart_count = 0
            
            # 监控推流状态
            self._thread = threading.Thread(target=self._monitor_stream, daemon=True)
            self._thread.start()
            if not self._frame_thread or not self._frame_thread.is_alive():
                self._frame_thread = threading.Thread(target=self._frame_loop, daemon=True)
                self._frame_thread.start()
            return True
            
        except Exception as e:
            logger.error(f"启动推流失败: {str(e)}")
            self._running = False
            self.process = None
            return False
            
    def _monitor_stream(self):
        """监控推流状态，支持自动重连"""
        while self._running:
            if self.process:
                returncode = self.process.poll()
                if returncode is not None:
                    # 推流进程已退出
                    logger.warning(f"推流进程退出，返回码: {returncode}")
                    if self._restart_count < self._max_restarts:
                        self._restart_count += 1
                        logger.info(f"等待5秒后重连 (第{self._restart_count}次)...")
                        time.sleep(5)
                        self._start_ffmpeg()
                    else:
                        logger.error("达到最大重连次数，停止推流")
                        self._running = False
                        break
            time.sleep(2)
        
    def stop_stream(self):
        """停止推流"""
        self._running = False
        self._started_at = None
        if self._frame_thread and threading.current_thread() is not self._frame_thread:
            self._frame_thread.join(timeout=5)
            self._frame_thread = None
        if self.process:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("推流已停止")
        
    def write_frame(self, frame_bytes: bytes):
        """写入视频帧（用于实时画面推流）"""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(frame_bytes)
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"写入帧失败: {str(e)}")
                self.stop_stream()

    def _frame_loop(self):
        """持续把摄像头/合成画面写入FFmpeg。"""
        from services.compositor import chromakey, compositor, camera_state

        frame_interval = 1.0 / max(self.config.fps if self.config else 30, 1)
        next_frame_at = time.time()

        while self._running:
            if not self.config:
                time.sleep(frame_interval)
                continue

            frame = camera_state.last_frame
            if frame is not None:
                if camera_state.use_chroma_key:
                    foreground, _ = chromakey.remove_background(frame)
                else:
                    foreground = frame
                output = compositor.composite(foreground)
            else:
                output = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
                cv2.putText(
                    output,
                    "Waiting for camera...",
                    (80, self.config.height // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.5,
                    (255, 255, 255),
                    3
                )

            if output.shape[1] != self.config.width or output.shape[0] != self.config.height:
                output = cv2.resize(output, (self.config.width, self.config.height))

            self.write_frame(np.ascontiguousarray(output).tobytes())

            next_frame_at += frame_interval
            sleep_for = next_frame_at - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_frame_at = time.time()
                
    def is_dry_run(self) -> bool:
        return bool(self._running and self.config and self.config.dry_run)

    def uptime_seconds(self) -> float:
        if not self._running or not self._started_at:
            return 0.0
        return max(0.0, time.time() - self._started_at)

    def is_running(self) -> bool:
        if self.is_dry_run():
            return True
        return self._running and self.process is not None and self.process.poll() is None

# 全局单例
streaming = StreamingService()
