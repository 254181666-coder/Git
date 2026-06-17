#!/usr/bin/env python3
"""简化测试：直接用纯色帧推流"""
import subprocess
import numpy as np
import time
import cv2

width, height = 1080, 1920
fps = 25

print(f"推流尺寸: {width}x{height}")
print("像素格式: BGR24")

# FFmpeg 命令（使用 RGB 格式）
cmd = [
    "ffmpeg",
    "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "rgb24",
    "-s", f"{width}x{height}",
    "-r", str(fps),
    "-i", "pipe:0",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-b:v", "3000k",
    "-pix_fmt", "yuv420p",
    "-g", "25",
    "-keyint_min", "25",
    "-sc_threshold", "0",
    "-f", "flv",
    "rtmp://localhost/live/test"
]

process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

# 使用高精度定时器
import time

# 创建渐变测试图案
print("开始推流，按 Ctrl+C 停止...")
frame_count = 0
frame_interval = 1.0 / fps
last_time = time.time()

try:
    while True:
        # 创建渐变图案 (BGR格式 - OpenCV默认)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 创建垂直渐变
        for y in range(height):
            frame[y, :, 0] = int(255 * y / height)  # B
            frame[y, :, 1] = 0                      # G
            frame[y, :, 2] = int(255 * (1 - y/height))  # R
        
        # 添加移动的方块
        y_pos = int((frame_count * 10) % height)
        frame[y_pos:y_pos+100, 440:640] = [255, 255, 255]  # BGR
        
        # 转换为 RGB 格式（OpenCV默认是BGR，FFmpeg rgb24需要RGB）
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 确保连续
        frame = np.ascontiguousarray(frame)
        
        # 写入 FFmpeg
        try:
            process.stdin.write(frame.tobytes())
        except BrokenPipeError:
            print("RTMP 连接断开")
            break
        
        frame_count += 1
        
        # 精确控制帧率
        elapsed = time.time() - last_time
        sleep_time = frame_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        last_time = time.time()
        
        # 每100帧输出一次状态
        if frame_count % 100 == 0:
            actual_fps = 100 / (time.time() - last_time + 100 * frame_interval)
            print(f"帧数: {frame_count}, 实际帧率: {actual_fps:.1f} fps")
        
except KeyboardInterrupt:
    print(f"\n推流停止，共 {frame_count} 帧")
    process.stdin.close()
    process.wait()
