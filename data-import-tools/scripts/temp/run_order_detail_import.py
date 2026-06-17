#!/usr/bin/env python3
"""直接调用import_order_detail来重新导入5月的订单文件"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("开始导入5月order_detail数据")
print("=" * 80)

from scripts.import_order_detail import main as import_order_detail
import_order_detail()

print("\n现在重新生成order_daily表...")

from scripts.import_data import generate_order_daily
generate_order_daily()

print("\n" + "=" * 80)
print("导入完成！")

print("\n现在验证一下5月的午夜场数据...")
from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()
print("\norder_detail表中5月的午夜场数据：")
cursor.execute('''
    SELECT data_date, COUNT(*) as cnt, SUM(actual_amount) as revenue
    FROM order_detail
    WHERE data_date >= '2026-05-01'
        AND time_period LIKE '%午夜%'
    GROUP BY data_date
    ORDER BY data_date
''')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} 单, 金额 ¥{row[2]:.2f}")

print("\norder_daily表中5月的午夜场数据：")
cursor.execute('''
    SELECT data_date, COUNT(*) as cnt, SUM(item_count), SUM(revenue)
    FROM order_daily
    WHERE data_date >= '2026-05-01'
        AND time_period = '午夜场'
    GROUP BY data_date
    ORDER BY data_date
''')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} 个维度, {row[2]} 单, 金额 ¥{row[3]:.2f}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
