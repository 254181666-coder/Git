#!/usr/bin/env python3
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

print("=" * 80)
print("🧹 开始清理 data/source 文件夹...")
print("=" * 80)
print(f"目标: 只保留 2026-05-06 的文件")

source_files = list(SOURCE_DIR.iterdir())
kept = []
moved = []

for f in source_files:
    if f.name.startswith('.'):
        continue
    
    # 判断是否是今天（05-06）的文件
    is_today = False
    if "20260506" in f.name or "_05_06.xlsx" in f.name or "2026_05_06" in f.name:
        is_today = True
    
    # 特殊处理 25nian.xlsx，这个是历史数据应该保留
    if f.name == "25nian.xlsx":
        is_today = True
    
    if is_today:
        kept.append(f)
    else:
        moved.append(f)

print(f"\n保留 {len(kept)} 个文件:")
for f in kept:
    print(f"  ✅ {f.name}")

print(f"\n移动 {len(moved)} 个文件到归档目录...")

# 移动旧文件到 source_history 或对应日期目录
source_history = ARCHIVE_DIR / "source_history"
source_history.mkdir(exist_ok=True)

for f in moved:
    # 尝试找日期
    date_str = None
    if "20260501" in f.name:
        date_str = "2026_05_01"
    elif "20260503" in f.name:
        date_str = "2026_05_03"
    elif "20260504" in f.name:
        date_str = "2026_05_04"
    elif "20260505" in f.name:
        date_str = "2026_05_05"
    
    dest_dir = None
    if date_str:
        dest_dir = ARCHIVE_DIR / f"source_{date_str}"
        dest_dir.mkdir(exist_ok=True)
    
    if dest_dir and dest_dir.exists():
        dest = dest_dir / f.name
    else:
        dest = source_history / f.name
    
    try:
        shutil.move(str(f), str(dest))
        print(f"  ✅ {f.name} -> {dest.parent.name}")
    except Exception as e:
        print(f"  ⚠️  {f.name}: {e}")

print("\n" + "=" * 80)
print("✅ 清理完成！")
print("\n现在 data/source 的内容:")
for f in sorted(SOURCE_DIR.iterdir()):
    if not f.name.startswith('.'):
        print(f"  - {f.name}")
print("=" * 80)
