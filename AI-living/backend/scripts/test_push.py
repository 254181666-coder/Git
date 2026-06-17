"""
测试用背景推流
用生成的背景图循环推流到RTMP服务器
"""
import subprocess
import sys

# 背景图路径
bg_path = "data/test_background.png"
rtmp_url = "rtmp://localhost/live/test"

# FFmpeg命令：循环读取图片推流
cmd = [
    "ffmpeg",
    "-loop", "1",              # 循环读取图片
    "-i", bg_path,             # 输入图片
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-b:v", "4000k",
    "-pix_fmt", "yuv420p",
    "-g", "60",
    "-c:a", "aac",
    "-b:a", "128k",
    "-ar", "44100",
    "-f", "flv",
    "-flvflags", "no_duration_filesize",
    rtmp_url
]

print(f"开始推流: {rtmp_url}")
print(f"使用背景图: {bg_path}")
print("按 Ctrl+C 停止推流")

try:
    process = subprocess.run(cmd)
except KeyboardInterrupt:
    print("\n推流已停止")
    sys.exit(0)
