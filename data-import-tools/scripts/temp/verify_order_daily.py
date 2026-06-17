#!/usr/bin/env python3
"""
验证order_daily表状态
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql


conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("验证order_daily表状态")
print("=" * 80)

# 检查order_daily表
print("\n【order_daily表】")
cursor.execute("SELECT MIN(data_date), MAX(data_date), COUNT(*) FROM order_daily")
min_date, max_date, count_daily = cursor.fetchone()
print(f"  日期范围: {min_date} ~ {max_date}")
print(f"  总记录数: {count_daily}")

cursor.execute("""
    SELECT data_date, COUNT(*) as cnt
    FROM order_daily
    WHERE data_date >= '2026-05-01'
    GROUP BY data_date
    ORDER BY data_date
""")
print("\n  5月份数据:")
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]} 条")

# 检查order_detail表
print("\n【order_detail表】")
cursor.execute("SELECT MIN(data_date), MAX(data_date), COUNT(*) FROM order_detail WHERE data_date IS NOT NULL")
min_date, max_date, count_detail = cursor.fetchone()
print(f"  日期范围: {min_date} ~ {max_date}")
print(f"  总记录数: {count_detail}")

cursor.execute("""
    SELECT data_date, COUNT(*) as cnt
    FROM order_detail
    WHERE data_date >= '2026-05-01'
    GROUP BY data_date
    ORDER BY data_date
""")
print("\n  5月份数据:")
dates_in_detail = []
for row in cursor.fetchall():
    print(f"    {row[0]}: {row[1]} 条")
    dates_in_detail.append(row[0])

# 对比
print("\n【对比检查】")
cursor.execute("""
    SELECT DISTINCT data_date
    FROM order_daily
    WHERE data_date >= '2026-05-01'
    ORDER BY data_date
""")
dates_in_daily = [row[0] for row in cursor.fetchall()]

missing_in_daily = [d for d in dates_in_detail if d not in dates_in_daily]

if missing_in_daily:
    print(f"  ⚠️  警告: order_detail有但order_daily缺失的日期: {missing_in_daily}")
else:
    print(f"  ✅ 5月份的数据在order_daily表中完整！")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("验证完成")
print("=" * 80)
