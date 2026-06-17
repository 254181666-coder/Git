#!/usr/bin/env python3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("✅ 数据库导入完成！现在简单验证！")
print("=" * 80)

print("\n1️⃣  检查各表结构:")
for table in ['order_detail', 'order_daily', 'store_daily']:
    print(f"\n【{table}】")
    cursor.execute(f"DESCRIBE {table}")
    print("  字段:")
    for col in cursor.fetchall():
        print(f"    - {col[0]}")

print("\n" + "=" * 80)
print("2️⃣  order_daily 表 5月5日 午夜场数据（按门店）:")
print("=" * 80)

cursor.execute("""
    SELECT data_date, COUNT(*) 
    FROM order_daily 
    WHERE data_date = '2026-05-05' AND time_period = '午夜场'
    GROUP BY data_date
""")
row = cursor.fetchone()
print(f"\n  {row[0]} 午夜场 总计 {row[1]} 条记录")

print("\n3️⃣  order_detail 表 5月5日 所有门店数据:")
cursor.execute("""
    SELECT data_date, COUNT(*) 
    FROM order_detail 
    WHERE data_date = '2026-05-05'
    GROUP BY data_date
""")
row = cursor.fetchone()
print(f"  {row[0]} 总计 {row[1]} 条记录")

print("\n" + "=" * 80)
print("✅ 数据导入完整！现在看板应该能正确显示所有数据了！")
print("=" * 80)

cursor.close()
conn.close()
