#!/usr/bin/env python3
"""测试贴片叠加推流效果"""
import subprocess
import cv2
import numpy as np
import os
import time

# 配置
bg_path = "data/test_background.png"
rtmp_url = "rtmp://localhost/live/test"
width, height = 1080, 1920
fps = 25

print("=== 贴片叠加推流测试 ===")
print(f"背景图: {bg_path}")
print(f"推流地址: {rtmp_url}")
print(f"分辨率: {width}x{height}")

# 启动FFmpeg推流进程
cmd = [
    "ffmpeg",
    "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{width}x{height}",
    "-r", str(fps),
    "-i", "pipe:0",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-b:v", "4000k",
    "-pix_fmt", "yuv420p",
    "-g", "50",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-f", "flv",
    rtmp_url
]

print("\n启动FFmpeg推流...")
process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

# 读取背景图
bg = cv2.imread(bg_path)
if bg is None:
    print("错误: 背景图不存在")
    exit(1)
bg = cv2.resize(bg, (width, height))

# 创建商品贴片（模拟）
overlay1 = np.zeros((200, 300, 3), dtype=np.uint8)
overlay1[:, :] = [52, 211, 153]  # 绿色背景
cv2.putText(overlay1, "SNACK 1", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
cv2.putText(overlay1, "$9.9", (90, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

overlay2 = np.zeros((200, 300, 3), dtype=np.uint8)
overlay2[:, :] = [251, 191, 36]  # 黄色背景
cv2.putText(overlay2, "SNACK 2", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
cv2.putText(overlay2, "$19.9", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

# 滚动文字
scroll_text = "LIMITED OFFER - 50% OFF ALL SNACKS! FOLLOW FOR MORE DEALS!"
scroll_x = width

print("开始推流，按 Ctrl+C 停止...")
frame_count = 0

try:
    while True:
        # 复制背景
        frame = bg.copy()
        
        # 叠加商品贴片1（左上）
        y1, y2 = 250, 250 + overlay1.shape[0]
        x1, x2 = 50, 50 + overlay1.shape[1]
        frame[y1:y2, x1:x2] = overlay1
        
        # 叠加商品贴片2（右上）
        y1, y2 = 250, 250 + overlay2.shape[0]
        x1, x2 = width - 350, width - 50
        frame[y1:y2, x1:x2] = overlay2
        
        # 滚动文字（底部）
        scroll_x -= 5
        if scroll_x < -len(scroll_text) * 30:
            scroll_x = width
        cv2.putText(frame, scroll_text, (scroll_x, height - 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # 直播标识
        cv2.putText(frame, "LIVE", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)
        
        # 写入帧
        process.stdin.write(frame.tobytes())
        
        frame_count += 1
        time.sleep(1.0 / fps)
        
except KeyboardInterrupt:
    print("\n\n推流已停止")
    process.stdin.close()
    process.wait()
    print(f"共推流 {frame_count} 帧")
