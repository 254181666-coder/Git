#!/usr/bin/env python3
"""调用import_data.py中修复后的generate_order_daily"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 直接导入并调用修复好的generate_order_daily
from scripts.import_data import generate_order_daily

print("=" * 80)
print("使用import_data.py中修复后的generate_order_daily")
print("=" * 80)

generate_order_daily()

print("\n" + "=" * 80)
print("现在验证5月份的数据完整性...")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql
conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

# 验证
cursor.execute("""
    SELECT DISTINCT data_date FROM order_daily WHERE data_date >= '2026-05-01' ORDER BY data_date
""")
daily_dates = [row[0] for row in cursor.fetchall()]

cursor.execute("""
    SELECT DISTINCT data_date FROM order_detail WHERE data_date >= '2026-05-01' ORDER BY data_date
""")
detail_dates = [row[0] for row in cursor.fetchall()]

print(f"\norder_detail 中有数据的5月份日期: {detail_dates}")
print(f"order_daily 中有数据的5月份日期: {daily_dates}")

missing_in_daily = [d for d in detail_dates if d not in daily_dates]
if missing_in_daily:
    print(f"\n⚠️ 仍然缺失: {missing_in_daily}")
else:
    print(f"\n✅ 完整！5月份数据齐全！")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("完成！")
print("=" * 80)
