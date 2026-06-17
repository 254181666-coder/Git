#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

print("=" * 80)
print("📂 检查 data/source 目录当前内容:")
print("=" * 80)
print(f"当前时间: {datetime.now()}")

source_files = sorted(SOURCE_DIR.iterdir())
print(f"\n当前有 {len([f for f in source_files if not f.name.startswith('.')])} 个文件:")
for f in source_files:
    if f.name.startswith('.'):
        continue
    size = f.stat().st_size
    print(f"  - {f.name} ({size} bytes)")

print("\n" + "=" * 80)
print("📂 检查已归档文件(archive/source_*):")
print("=" * 80)
date_dirs = sorted([d for d in ARCHIVE_DIR.iterdir() if d.is_dir() and d.name.startswith("source_2026_")])
print(f"\n共有 {len(date_dirs)} 个日期归档目录:")
for d in date_dirs[-6:]:
    count = len(list(d.iterdir()))
    print(f"  - {d.name}: {count} 个文件")

print("\n" + "=" * 80)
print("📂 检查 source_history:")
print("=" * 80)
source_hist = ARCHIVE_DIR / "source_history"
if source_hist.exists():
    count = len(list(source_hist.iterdir()))
    print(f"\n  source_history 目录: {count} 个文件")

print("\n" + "=" * 80)
