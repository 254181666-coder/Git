#!/usr/bin/env python3
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

print("=" * 80)
print("🧹 最后清理 source 目录")
print("=" * 80)

kept_files = []
moved_files = []

for f in SOURCE_DIR.iterdir():
    if f.name.startswith('.'):
        continue
    
    is_today = False
    if '20260510' in f.name or '_05_10.xlsx' in f.name or '2026_05_10' in f.name:
        is_today = True
    if f.name == '25nian.xlsx':
        is_today = True
    
    if is_today:
        kept_files.append(f)
    else:
        moved_files.append(f)

print(f"\n✅ 保留的文件: {len(kept_files)}")
for f in kept_files:
    print(f"  - {f.name}")

print(f"\n📦 移动到归档目录的文件: {len(moved_files)}")

for f in moved_files:
    date_str = None
    if '20260506' in f.name:
        date_str = '2026_05_06'
    elif '20260507' in f.name:
        date_str = '2026_05_07'
    elif '20260508' in f.name:
        date_str = '2026_05_08'
    elif '20260509' in f.name:
        date_str = '2026_05_09'
    
    dest_dir = None
    if date_str:
        dest_dir = ARCHIVE_DIR / f"source_{date_str}"
        dest_dir.mkdir(exist_ok=True)
    
    if dest_dir and dest_dir.exists():
        dest = dest_dir / f.name
    else:
        dest = ARCHIVE_DIR / "source_history" / f.name
    
    try:
        shutil.move(str(f), str(dest))
        print(f"  ✅ {f.name} -> {dest.parent.name}")
    except Exception as e:
        print(f"  ⚠️ {f.name}: {e}")

print("\n" + "=" * 80)
print("📊 完整数据总结")
print("=" * 80)

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

for table in ["order_detail", "order_daily", "store_daily"]:
    print(f"\n【{table}】")
    cursor.execute(f"""
        SELECT data_date, COUNT(*) FROM {table} 
        WHERE data_date >= '2026-05-07'
        GROUP BY data_date 
        ORDER BY data_date
    """)
    for row in cursor.fetchall():
        print(f"  ✅ {row[0]}: {row[1]} 条")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 100% 完成！")
print("=" * 80)
