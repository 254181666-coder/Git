#!/usr/bin/env python3
"""详细检查5月份order_detail中的午夜场数据"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("检查5月1日至5月4日的午夜场数据")
print("=" * 80)

# 检查order_detail中5月1日至4日的午夜场数据
for day in range(1, 6):
    date_str = f"2026-05-{day:02d}"
    print(f"\n【{date_str}】order_detail中的记录：")
    cursor.execute("""
        SELECT COUNT(*), SUM(actual_amount), 
               GROUP_CONCAT(DISTINCT store_id),
               GROUP_CONCAT(DISTINCT time_period)
        FROM order_detail
        WHERE data_date = %s
          AND (time_period LIKE '%%午夜%%' OR HOUR(open_time) BETWEEN 0 AND 5)
    """, (date_str,))
    count, revenue, stores, time_periods = cursor.fetchone()
    print(f"  符合条件的记录: {count} 单, 金额 ¥{revenue}, 门店: {stores}, time_period: {time_periods}")

print("\n" + "-" * 80)
print("\n现在检查5月2日至4日中0-5点开房的实际订单：")
for day in range(2, 5):
    date_str = f"2026-05-{day:02d}"
    print(f"\n{date_str} 0-5点的订单：")
    cursor.execute("""
        SELECT store_id, COUNT(*), SUM(actual_amount)
        FROM order_detail
        WHERE data_date = %s
          AND HOUR(open_time) BETWEEN 0 AND 5
        GROUP BY store_id
    """, (date_str,))
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  门店 {row[0]}: {row[1]} 单, ¥{row[2]}")
    else:
        print(f"  无记录")

# 再检查一下order_daily中这几天的情况
print("\n" + "-" * 80)
print("\norder_daily表中5月1-4日的所有数据：")
cursor.execute("""
    SELECT data_date, time_period, COUNT(*), SUM(item_count), SUM(revenue)
    FROM order_daily
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-04'
    GROUP BY data_date, time_period
    ORDER BY data_date, time_period
""")
for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]}: {row[2]} 维度, {row[3]} 单, ¥{row[4]}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
