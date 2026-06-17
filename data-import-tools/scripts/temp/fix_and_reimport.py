#!/usr/bin/env python3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "data" / "logs"

print("=" * 80)
print("1. 删除锁定文件...")
print("=" * 80)

lock_files = list(LOGS_DIR.glob(".import_lock*"))
for f in lock_files:
    f.unlink()
    print(f"✅ 已删除: {f.name}")

print("\n" + "=" * 80)
print("2. 重新运行 import_order_detail...")
print("=" * 80)
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_order_detail import main as import_orders
import_orders()

print("\n" + "=" * 80)
print("3. 重新运行 import_data...")
print("=" * 80)
from scripts.import_data import main as import_main
import_main()

print("\n" + "=" * 80)
print("✅ 完整导入完成！现在验证！")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("\n【store_daily 表 2026-05-05】")
cursor.execute("""
    SELECT data_date, store_name, COUNT(*) 
    FROM store_daily 
    WHERE data_date = '2026-05-05'
    GROUP BY data_date, store_name
    ORDER BY store_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]} - {row[1]}: {row[2]} 条")

print("\n【order_daily 表 2026-05-05 午夜场】")
cursor.execute("""
    SELECT data_date, store_name, COUNT(*) 
    FROM order_daily 
    WHERE data_date = '2026-05-05' AND time_period = '午夜场'
    GROUP BY data_date, store_name
    ORDER BY store_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]} - {row[1]}: {row[2]} 条")

print("\n【order_detail 表 2026-05-05 按门店】")
cursor.execute("""
    SELECT data_date, store_name, COUNT(*) 
    FROM order_detail 
    WHERE data_date = '2026-05-05'
    GROUP BY data_date, store_name
    ORDER BY store_name
""")
for row in cursor.fetchall():
    print(f"  {row[0]} - {row[1]}: {row[2]} 单")

cursor.close()
conn.close()
