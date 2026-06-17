#!/usr/bin/env python3
"""检查order_daily和order_detail中的午夜场数据"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("检查5月份的午夜场数据")
print("=" * 80)

# 检查order_detail中的5月份午夜场数据
print("\n【1】order_detail 表中的5月份午夜场数据（按天统计）：")
cursor.execute("""
    SELECT data_date, COUNT(*) as cnt, SUM(actual_amount) as revenue
    FROM order_detail
    WHERE data_date >= '2026-05-01'
      AND time_period LIKE '%午夜%'
    GROUP BY data_date
    ORDER BY data_date
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} 单, 金额 ¥{row[2]}")

print("\n【2】order_daily 表中的5月份午夜场数据（按天统计）：")
cursor.execute("""
    SELECT data_date, COUNT(*) as cnt, SUM(item_count), SUM(revenue)
    FROM order_daily
    WHERE data_date >= '2026-05-01'
      AND time_period = '午夜场'
    GROUP BY data_date
    ORDER BY data_date
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} 个维度, {row[2]} 单, 金额 ¥{row[3]}")

# 检查order_detail中的time_period值分布
print("\n【3】order_detail 中5月的time_period值分布：")
cursor.execute("""
    SELECT time_period, COUNT(*) as cnt
    FROM order_detail
    WHERE data_date >= '2026-05-01'
    GROUP BY time_period
""")
for row in cursor.fetchall():
    print(f"  '{row[0]}': {row[1]} 条")

# 检查松原一店的5月1日数据
print("\n【4】松原一店5月1日的详细数据：")
cursor.execute("""
    SELECT * FROM order_detail
    WHERE data_date = '2026-05-01'
      AND store_id = 10
""")
row = cursor.fetchone()
if row:
    cursor.execute("DESCRIBE order_detail")
    cols = [c[0] for c in cursor.fetchall()]
    print("  order_detail中的记录：")
    for i, col in enumerate(cols):
        if col in ['data_date', 'time_period', 'order_type', 'source_channel', 'actual_amount']:
            print(f"    {col}: {row[i]}")

print("\n  查看order_daily中的对应记录：")
cursor.execute("""
    SELECT * FROM order_daily
    WHERE data_date = '2026-05-01'
      AND store_name = '松原一店'
""")
daily_row = cursor.fetchone()
if daily_row:
    cursor.execute("DESCRIBE order_daily")
    cols = [c[0] for c in cursor.fetchall()]
    for i, col in enumerate(cols):
        print(f"    {col}: {daily_row[i]}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
