#!/usr/bin/env python3
import sys
from pathlib import Path
import shutil
import subprocess
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
desktop_path = Path.home() / "Desktop"
source_dir = PROJECT_ROOT / "data" / "source"
logs_dir = PROJECT_ROOT / "data" / "logs"

# 1. 清理source目录
print("1. 清理source目录...")
for f in source_dir.glob("*.xlsx"):
    f.unlink()
for f in source_dir.glob("*.csv"):
    f.unlink()

# 2. 复制日营业数据
print("\n2. 复制文件...")
source_file = desktop_path / "日营业数据表_21109.xlsx"
target_file = source_dir / "日营业数据表_21109.xlsx"
shutil.copy(source_file, target_file)
print(f"✓ 日营业数据已复制")

# 3. 检查是否有其他2026年5月的文件需要复制？
print("\n3. 删除锁定文件...")
for lock_file in logs_dir.glob(".import_lock*"):
    lock_file.unlink()
    print(f"✓ 删除锁定文件: {lock_file}")

print("\n✅ 准备完成！现在运行import_data.py...")

# 运行导入
print("\n4. 运行数据导入...")
result = subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "scripts" / "import_data.py")],
    cwd=str(PROJECT_ROOT),
    capture_output=False
)
print(f"\n返回码: {result.returncode}")
