#!/usr/bin/env python3
"""删除锁定文件并导入"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

logs_dir = PROJECT_ROOT / "data" / "logs"
lock_files = list(logs_dir.glob(".import_lock_202605*"))

print(f"找到 {len(lock_files)} 个锁定文件：")
for lock_file in lock_files:
    print(f"  {lock_file.name}")

print("\n正在删除锁定文件...")
for lock_file in lock_files:
    lock_file.unlink()

print("\n锁定文件已删除！现在运行导入...")

from scripts.import_data import main
main()
