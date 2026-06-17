#!/usr/bin/env python3
"""对比4月和5月的午夜场数据情况"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("对比4月和5月的午夜场数据")
print("=" * 80)

print("\n【4月份】order_detail中的午夜场数据：")
cursor.execute("""
    SELECT data_date, COUNT(*), SUM(actual_amount)
    FROM order_detail
    WHERE data_date >= '2026-04-01' AND data_date <= '2026-04-30'
      AND (time_period LIKE '%%午夜%%' OR HOUR(open_time) BETWEEN 0 AND 5)
    GROUP BY data_date
    ORDER BY data_date
""")
april_data = cursor.fetchall()
for row in april_data:
    print(f"  {row[0]}: {row[1]} 单, ¥{row[2]}")
print(f"\n  4月共有 {len(april_data)} 天有午夜场数据")

print("\n【5月份】order_detail中的午夜场数据：")
cursor.execute("""
    SELECT data_date, COUNT(*), SUM(actual_amount)
    FROM order_detail
    WHERE data_date >= '2026-05-01'
      AND (time_period LIKE '%%午夜%%' OR HOUR(open_time) BETWEEN 0 AND 5)
    GROUP BY data_date
    ORDER BY data_date
""")
may_data = cursor.fetchall()
for row in may_data:
    print(f"  {row[0]}: {row[1]} 单, ¥{row[2]}")
print(f"\n  5月共有 {len(may_data)} 天有午夜场数据")

print("\n" + "-" * 80)
print("现在检查5月导入日志看看发生了什么...")

import os
logs_dir = PROJECT_ROOT / "data" / "logs"
for day in range(1, 6):
    log_file = logs_dir / f"import_202605{day:02d}.log"
    if log_file.exists():
        print(f"\n--- {log_file.name} ---")
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "order_detail" in content.lower():
                print("  该次导入涉及order_detail表！")
            else:
                print("  该次导入**没有**涉及order_detail表！")

# 检查最早和最晚的data_date
print("\n" + "-" * 80)
cursor.execute("SELECT MIN(data_date), MAX(data_date) FROM order_detail")
min_date, max_date = cursor.fetchone()
print(f"order_detail 表的日期范围：{min_date} 至 {max_date}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
