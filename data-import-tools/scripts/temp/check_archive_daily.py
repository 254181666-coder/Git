#!/usr/bin/env python3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

print("=" * 80)
print("📂 检查归档目录里的日营业数据文件:")
print("=" * 80)

print("\n检查 source_2026_05_09 目录:")
dir_09 = ARCHIVE_DIR / "source_2026_05_09"
if dir_09.exists():
    for f in sorted(dir_09.iterdir()):
        if '日营业' in f.name:
            print(f"  ✅ {f.name}")
            print(f"    路径: {f}")

print("\n检查 source_2026_05_10 目录:")
dir_10 = ARCHIVE_DIR / "source_2026_05_10"
if dir_10.exists():
    for f in sorted(dir_10.iterdir()):
        if '日营业' in f.name:
            print(f"  ✅ {f.name}")
            print(f"    路径: {f}")

print("\n检查 source_history 目录:")
source_hist = ARCHIVE_DIR / "source_history"
if source_hist.exists():
    for f in sorted(source_hist.iterdir()):
        if '日营业' in f.name and ('0509' in f.name or '05_09' in f.name or '0510' in f.name or '05_10' in f.name):
            print(f"  ✅ {f.name}")
            print(f"    路径: {f}")

print("\n" + "=" * 80)
print("📂 当前 data/source 里的日营业数据文件:")
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
if SOURCE_DIR.exists():
    for f in sorted(SOURCE_DIR.iterdir()):
        if '日营业' in f.name:
            print(f"  ✅ {f.name}")

print("=" * 80)
