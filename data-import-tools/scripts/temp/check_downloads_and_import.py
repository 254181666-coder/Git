#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import shutil

print("=" * 80)
print("检查下载文件夹文件")
print("=" * 80)

# 路径设置
HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE = PROJECT_ROOT / "data" / "source"

print(f"\n下载文件夹: {DOWNLOADS}")

if DOWNLOADS.exists():
    print("\n所有最近的文件:")
    files = sorted(DOWNLOADS.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[:20]:
        if not f.name.startswith('.') and f.is_file():
            dt = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  {dt.strftime('%Y-%m-%d %H:%M')} - {f.name}")

print("\n" + "=" * 80)
print("当前 data/source 目录内容:")
print("=" * 80)
if SOURCE.exists():
    for f in sorted(SOURCE.iterdir()):
        if not f.name.startswith('.'):
            print(f"  - {f.name}")

print("\n" + "=" * 80)
print("请告诉我需要导入哪些文件名? 我会帮你复制到 source 并重新导入!")
print("=" * 80)
