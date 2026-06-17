
"""
检查store_daily表的时段字段数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

print("=== 检查store_daily表时段字段数据...")
print()

sql = """
SELECT sd.data_date, s.store_name,
       sd.customers_before_18,
       sd.customers_18_to_24,
       sd.customers_after_00,
       sd.efficiency
FROM store_daily sd
JOIN stores s ON s.id = sd.store_id
ORDER BY sd.data_date DESC
LIMIT 20
"""

df = query(sql)
print("store_daily时段字段前20条:")
print(df)

print(f"\n\n=== 时段字段数据类型和统计 ===\n")
if not df.empty:
    print(f"customers_before_18 的唯一值: {df['customers_before_18'].unique()}")
    print(f"customers_18_to_24 的唯一值: {df['customers_18_to_24'].unique()}")
    print(f"customers_after_00 的唯一值: {df['customers_after_00'].unique()}")
    print(f"efficiency 的唯一值: {df['efficiency'].unique()}")

print(f"\n\n=== 查看表结构 ===\n")
sql2 = "PRAGMA table_info(store_daily);"
df2 = query(sql2)
print(df2)

