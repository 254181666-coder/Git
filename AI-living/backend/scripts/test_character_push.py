#!/usr/bin/env python3
"""测试虚拟人物（模拟绿幕抠图效果）+ 贴片合成推流"""
import subprocess
import cv2
import numpy as np
import time
import os

# 配置
bg_path = "data/test_background.png"
char_path = "data/virtual_character.png"
rtmp_url = "rtmp://localhost/live/test"
width, height = 1080, 1920
fps = 25

print("=== 虚拟人物 + 贴片合成推流测试 ===")
print(f"背景图: {bg_path}")
print(f"虚拟人物: {char_path}")
print(f"推流地址: {rtmp_url}")

# 启动FFmpeg推流进程（使用BGR格式，无alpha）
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
    "-f", "flv",
    rtmp_url
]

print("\n启动FFmpeg推流...")
process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

# 读取背景图（BGR）
bg = cv2.imread(bg_path)
if bg is None:
    print("错误: 背景图不存在")
    exit(1)
bg = cv2.resize(bg, (width, height))

# 读取虚拟人物（带透明通道）
char_rgba = cv2.imread(char_path, cv2.IMREAD_UNCHANGED)
if char_rgba is None:
    print("错误: 虚拟人物图片不存在")
    exit(1)
char_rgba = cv2.resize(char_rgba, (400, 667))

# 创建商品贴片（BGR格式）
overlay1 = np.zeros((200, 300, 3), dtype=np.uint8)
overlay1[:, :] = [52, 211, 153]
cv2.putText(overlay1, "SNACK 1", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
cv2.putText(overlay1, "$9.9", (90, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

overlay2 = np.zeros((200, 300, 3), dtype=np.uint8)
overlay2[:, :] = [251, 191, 36]
cv2.putText(overlay2, "SNACK 2", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
cv2.putText(overlay2, "$19.9", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

# 滚动文字
scroll_text = "LIMITED OFFER - FOLLOW FOR MORE DEALS!"
scroll_x = width

# 人物位置（底部居中）
char_x = (width - char_rgba.shape[1]) // 2
char_y = height - char_rgba.shape[0] - 100

print("开始推流，按 Ctrl+C 停止...")
frame_count = 0

def blend_char_to_bgr(background_bgr, char_rgba, x, y):
    """将RGBA人物叠加到BGR背景上，返回BGR"""
    h, w = char_rgba.shape[:2]
    alpha = char_rgba[:, :, 3] / 255.0
    
    y1, y2 = y, min(y + h, background_bgr.shape[0])
    x1, x2 = x, min(x + w, background_bgr.shape[1])
    
    overlay_h = y2 - y1
    overlay_w = x2 - x1
    
    if overlay_h <= 0 or overlay_w <= 0:
        return background_bgr
    
    char_crop = char_rgba[:overlay_h, :overlay_w]
    alpha_crop = alpha[:overlay_h, :overlay_w]
    
    result = background_bgr.copy()
    
    for c in range(3):
        bg_part = result[y1:y2, x1:x2, c].astype(float)
        fg_part = char_crop[:, :, c].astype(float)
        result[y1:y2, x1:x2, c] = (bg_part * (1 - alpha_crop) + fg_part * alpha_crop).astype(np.uint8)
    
    return result

try:
    while True:
        # 每帧都复制背景
        frame = bg.copy()
        
        # 叠加虚拟人物（RGBA to BGR blend）
        frame = blend_char_to_bgr(frame, char_rgba, char_x, char_y)
        
        # 叠加商品贴片1（左上）
        y1, y2 = 250, 250 + overlay1.shape[0]
        x1, x2 = 50, 50 + overlay1.shape[1]
        frame[y1:y2, x1:x2] = overlay1
        
        # 叠加商品贴片2（右上）
        y1, y2 = 250, 250 + overlay2.shape[0]
        x1, x2 = width - 350, width - 50
        frame[y1:y2, x1:x2] = overlay2
        
        # 滚动文字
        scroll_x -= 5
        if scroll_x < -len(scroll_text) * 30:
            scroll_x = width
        cv2.putText(frame, scroll_text, (scroll_x, height - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        
        # LIVE 标识
        cv2.putText(frame, "LIVE", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)
        
        # 确保内存连续（解决滚屏/撕裂问题）
        frame = np.ascontiguousarray(frame)
        process.stdin.write(frame.tobytes())
        
        frame_count += 1
        time.sleep(1.0 / fps)
        
except KeyboardInterrupt:
    print("\n\n推流已停止")
    process.stdin.close()
    process.wait()
    print(f"共推流 {frame_count} 帧")
