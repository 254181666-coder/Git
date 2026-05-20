#!/usr/bin/env python3
"""
检查为什么 2026-05-14 没有上东店数据
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query

print("=" * 80)
print("详细检查上东店数据缺失问题")
print("=" * 80)

# 1. 检查上东(id=366)和上东店(id=5)最近 10 天的数据
print("\n1. 上东(id=366)最近10天数据:")
df_shangdong = query("""
    SELECT data_date, total_revenue, stored_card_sales, online_groupbuy
    FROM store_daily 
    WHERE store_id = 366
      AND data_date >= '2026-05-04'
    ORDER BY data_date DESC
""")
print(df_shangdong.to_string())

print("\n2. 上东店(id=5)最近10天数据:")
df_shangdongdian = query("""
    SELECT data_date, total_revenue, stored_card_sales, online_groupbuy
    FROM store_daily 
    WHERE store_id = 5
      AND data_date >= '2026-05-04'
    ORDER BY data_date DESC
""")
print(df_shangdongdian.to_string())

# 3. 检查 store_daily 表中最近几天有哪些门店有数据
print("\n3. 2026-05-13 到 2026-05-14 有数据的门店:")
df_recent_stores = query("""
    SELECT DISTINCT s.store_name, sd.data_date
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE sd.data_date IN ('2026-05-13', '2026-05-14')
    ORDER BY sd.data_date DESC, s.store_name
""")
print(df_recent_stores.to_string())
