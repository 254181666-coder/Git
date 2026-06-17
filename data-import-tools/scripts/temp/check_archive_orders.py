#!/usr/bin/env python3
"""检查归档数据中的order_export文件，看看5月的订单数据是否缺失"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

print("=" * 80)
print("检查归档数据中的order_export文件")
print("=" * 80)

archive_dir = PROJECT_ROOT / "data" / "archive"

# 检查source_history目录
source_history_dir = archive_dir / "source_history"
if source_history_dir.exists():
    print(f"\n【1】检查 {source_history_dir} 中的文件：")
    order_files = list(source_history_dir.glob("order_export*.csv"))
    print(f"\n  找到 {len(order_files)} 个order_export文件：")
    order_files.sort(key=lambda f: f.name)
    for f in order_files:
        print(f"    {f.name}")

# 检查source_2026_05_01等目录
print("\n【2】检查分日期的归档目录：")
for day in range(1, 6):
    date_dir = archive_dir / f"source_2026_05_{day:02d}"
    if date_dir.exists():
        print(f"\n{date_dir.name}:")
        order_files = list(date_dir.glob("order_export*.csv"))
        if order_files:
            for f in order_files:
                print(f"  ✓ {f.name}")
        else:
            print(f"  ✗ 没有找到order_export文件！")
        
        print(f"  目录内所有文件：")
        for f in date_dir.glob("*"):
            print(f"    - {f.name}")

print("\n" + "=" * 80)
print("\n检查4月同期的归档对比：")
for day in range(25, 31):
    date_dir = archive_dir / f"source_2026_04_{day:02d}"
    if date_dir.exists():
        order_files = list(date_dir.glob("order_export*.csv"))
        status = "✓" if order_files else "✗"
        print(f"{date_dir.name}: {status} {len(order_files)} 个order_export文件")

print("\n" + "=" * 80)
