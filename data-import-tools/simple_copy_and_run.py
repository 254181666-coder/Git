#!/usr/bin/env python3
import sys
from pathlib import Path
import shutil
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parent
desktop_path = Path.home() / "Desktop"
source_dir = PROJECT_ROOT / "data" / "source"
logs_dir = PROJECT_ROOT / "data" / "logs"

# 1. 复制文件
print("1. 复制文件...")
source_file = desktop_path / "日营业数据表_21109.xlsx"
target_file = source_dir / "日营业数据表_21109.xlsx"

shutil.copy(source_file, target_file)
print(f"✓ 文件已复制到: {target_file}")

# 2. 删除锁定文件
print("\n2. 删除锁定文件...")
import glob
for lock_file in logs_dir.glob(".import_lock*"):
    lock_file.unlink()
    print(f"✓ 删除了: {lock_file}")

# 3. 运行现有的import_data.py
print("\n3. 运行数据导入...")
result = subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "scripts" / "import_data.py")],
    capture_output=False,
    cwd=str(PROJECT_ROOT),
    text=True
)
print(result.stdout)
if result.stderr:
    print(result.stderr)

print("\n✅ 完成！")
