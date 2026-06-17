#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("🎯 最后修复：把 05-10 的日营业数据也导入")
print("=" * 80)

# 1. 从 source_history 把 05-10 的日营业数据找回来
file_10_daily = ARCHIVE_DIR / "source_history" / "日营业数据表_20644.xlsx"
file_09_daily = ARCHIVE_DIR / "source_2026_05_09" / "日营业数据表_20531.xlsx"

files_to_copy = []
if file_09_daily.exists():
    files_to_copy.append(file_09_daily)
if file_10_daily.exists():
    files_to_copy.append(file_10_daily)

print("\n复制文件到 source 目录:")
for f in files_to_copy:
    dest = SOURCE_DIR / f.name
    shutil.copy2(f, dest)
    print(f"  ✅ {f.name}")

# 2. 删除锁定文件，重新运行导入
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
lock_files = list(LOGS_DIR.glob(".import_lock*"))
for f in lock_files:
    f.unlink()
    print(f"\n✅ 删除锁定文件: {f.name}")

print("\n" + "=" * 80)
print("📦 运行完整数据导入...")
print("=" * 80)

from scripts.import_data import main
main()

print("\n" + "=" * 80)
print("✅ 最后验证...")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

dates_to_check = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]

for table in ["order_detail", "store_daily", "order_daily"]:
    print(f"\n【{table}】")
    for date_str in dates_to_check:
        cursor.execute(f"""
            SELECT COUNT(*) FROM {table} WHERE data_date = %s
        """, (date_str,))
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {date_str}: {count} 条")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 100% 完成！")
print("=" * 80)
