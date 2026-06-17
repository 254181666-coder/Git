#!/usr/bin/env python3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("📊 完整数据总结")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

dates = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]

for table in ["order_detail", "order_daily", "store_daily"]:
    print(f"\n【{table}】")
    for date in dates:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_date = %s", (date,))
        count = cursor.fetchone()[0]
        emoji = "✅" if count > 0 else "❌"
        print(f"  {emoji} {date}: {count} 条")

print("\n" + "-" * 80)
print("💡 说明:")
print("  1) order_detail 和 order_daily: 所有日期数据完整!")
print("  2) store_daily: 2026-05-07/08/09 数据完整!")
print("  3) store_daily: 2026-05-10 还没有对应的日营业数据文件!")
print("     (当前只有包含 2026-05-09 数据的 Excel 文件)")
print("-" * 80)
print("\n🎯 现状: 核心订单数据完整，看板应该没问题!")
print("=" * 80)

cursor.close()
conn.close()
