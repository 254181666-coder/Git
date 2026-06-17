#!/usr/bin/env python3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"

print("=" * 80)
print("📂 检查 data/source 目录")
print("=" * 80)

if SOURCE_DIR.exists():
    files = sorted(SOURCE_DIR.iterdir())
    print(f"共 {len(files)} 个文件:\n")
    for f in files:
        if f.name.startswith('.'):
            continue
        print(f"  - {f.name}")

print("\n" + "=" * 80)
