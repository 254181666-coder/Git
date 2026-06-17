#!/usr/bin/env python3
"""将source_history中的5月order_export文件复制回input目录并重新导入"""
import sys
from pathlib import Path
import shutil
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

source_history_dir = PROJECT_ROOT / "data" / "archive" / "source_history"
source_dir = PROJECT_ROOT / "data" / "source"

print("=" * 80)
print("重新导入5月order_export文件")
print("=" * 80)

# 找到需要重新导入的order_export文件
order_files = [
    "order_export_19865_20260501093328.csv",  # 5月1日数据
    "order_export_20033_20260503093318.csv",  # 5月2,3日数据
    "order_export_20106_20260504093308.csv"   # 5月3,4日数据
]

print(f"\n准备复制 {len(order_files)} 个文件到 {source_dir}：")

copied_files = []
for filename in order_files:
    src = source_history_dir / filename
    if src.exists():
        dest = source_dir / filename
        shutil.copy2(src, dest)
        print(f"  ✓ {filename}")
        copied_files.append(dest)
    else:
        print(f"  ✗ {filename} 不存在")

if copied_files:
    print(f"\n成功复制了 {len(copied_files)} 个文件！")
    
    # 现在让我们手动执行一次导入（不直接运行完整脚本，因为需要防止自动归档）
    print(f"\n现在运行导入脚本...")
    
    # 运行import_data.py
    from scripts.import_data import main
    main()
    
else:
    print("\n没有文件需要复制！")

print("\n" + "=" * 80)
