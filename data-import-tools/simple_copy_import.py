#!/usr/bin/env python3
import sys
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
downloads_dir = Path("/Users/ann/Downloads")
source_dir = PROJECT_ROOT / "data" / "source"
logs_dir = PROJECT_ROOT / "data" / "logs"

# 清空 source 文件夹
print("清理 source 文件夹...")
for f in source_dir.glob("*.xlsx"):
    f.unlink()
for f in source_dir.glob("*.csv"):
    f.unlink()

# 复制文件
files_to_copy = [
    "日营业数据表_21103.xlsx",
    "会员储值订单表_2026_05_16.xlsx",
    "商品销售明细_-_商品+包厢维度_2026_05_16.xlsx",
    "商品销售汇总_2026_05_16.xlsx"
]

print("\n复制文件：")
for filename in files_to_copy:
    src = downloads_dir / filename
    if src.exists():
        print(f"✓ {filename}")
        shutil.copy(src, source_dir / filename)
    else:
        # 尝试找带 (1) 的版本
        if filename.startswith("日营业"):
            src2 = downloads_dir / "日营业数据表_21103 (1).xlsx"
            if src2.exists():
                print(f"✓ 日营业数据表_21103 (1).xlsx")
                shutil.copy(src2, source_dir / "日营业数据表_21103.xlsx")

print(f"\nsource 文件夹内容：{[f.name for f in source_dir.glob('*.xlsx')]}")

# 删除锁定文件
print("\n检查锁定文件...")
from datetime import date
today = date.today()
today_lock = logs_dir / f".import_lock_{today.strftime('%Y%m%d')}"
if today_lock.exists():
    print(f"删除 {today_lock.name}")
    today_lock.unlink()

# 检查是否有其他锁定文件
for lock in logs_dir.glob(".import_lock_*"):
    print(f"删除 {lock.name}")
    lock.unlink()

print("\n准备完成！现在可以运行：python3 scripts/import_data.py")
