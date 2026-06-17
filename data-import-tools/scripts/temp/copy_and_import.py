#!/usr/bin/env python3
from pathlib import Path
import shutil

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE = PROJECT_ROOT / "data" / "source"

print("=" * 80)
print("1. 复制日营业数据表_20268.xlsx 到 source")
print("=" * 80)

src = DOWNLOADS / "日营业数据表_20268.xlsx"
dest = SOURCE / "日营业数据表_20268.xlsx"

if src.exists():
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"✅ 复制成功!")
    else:
        print(f"⚠️  文件已存在，跳过!")
else:
    print(f"❌ 源文件不存在!")

print("\n" + "=" * 80)
print("2. 当前 source 目录文件:")
print("=" * 80)
for f in sorted(SOURCE.iterdir()):
    if not f.name.startswith('.'):
        print(f"  - {f.name}")

print("\n" + "=" * 80)
print("3. 现在运行完整导入...")
print("=" * 80)

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_data import main as import_main

import_main()

print("\n" + "=" * 80)
print("✅ 导入完成！现在验证数据！")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("\nstore_daily 表 2026-05-05 的数据:")
cursor.execute("""
    SELECT data_date, store_id, COUNT(*) 
    FROM store_daily 
    WHERE data_date = '2026-05-05'
    GROUP BY data_date, store_id
    ORDER BY store_id
""")
for row in cursor.fetchall():
    print(f"  {row[0]} 店 {row[1]}: {row[2]} 条")

print("\nstore_daily 表 2026-05-06 的数据:")
cursor.execute("""
    SELECT data_date, store_id, COUNT(*) 
    FROM store_daily 
    WHERE data_date = '2026-05-06'
    GROUP BY data_date, store_id
    ORDER BY store_id
""")
for row in cursor.fetchall():
    print(f"  {row[0]} 店 {row[1]}: {row[2]} 条")

print("\norder_daily 表 2026-05-05 的午夜数据:")
cursor.execute("""
    SELECT data_date, store_id, COUNT(*) 
    FROM order_daily 
    WHERE data_date = '2026-05-05' AND time_period = '午夜场'
    GROUP BY data_date, store_id
    ORDER BY store_id
""")
for row in cursor.fetchall():
    print(f"  {row[0]} 店 {row[1]}: {row[2]} 条")

cursor.close()
conn.close()
