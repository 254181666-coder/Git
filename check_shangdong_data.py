#!/usr/bin/env python3
"""
检查上东店在 2026-05-14 和 2025-05-14 的数据
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query

print("=" * 80)
print("检查上东店数据")
print("=" * 80)

# 1. 查看所有门店
print("\n1. 查看 stores 表所有门店:")
stores_df = query("SELECT id, store_name FROM stores")
print(stores_df.to_string())

# 2. 查看 2026-05-14 的 store_daily 数据
print("\n2. 查看 2026-05-14 的 store_daily 数据:")
df_2026 = query("""
    SELECT 
        s.store_name,
        sd.*
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE sd.data_date = '2026-05-14'
""")
print(df_2026.to_string())

# 3. 查看 2025-05-14 的 store_daily 数据
print("\n3. 查看 2025-05-14 的 store_daily 数据:")
df_2025 = query("""
    SELECT 
        s.store_name,
        sd.*
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE sd.data_date = '2025-05-14'
""")
print(df_2025.to_string())

# 4. 查看最近几天上东相关的记录
print("\n4. 查看最近一周包含'上东'的 store_daily 记录:")
df_recent = query("""
    SELECT 
        s.store_name,
        sd.data_date,
        sd.total_revenue,
        sd.stored_card_sales,
        sd.online_groupbuy
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE s.store_name LIKE '%上东%'
      AND sd.data_date >= '2026-05-10'
    ORDER BY sd.data_date DESC
""")
print(df_recent.to_string())
