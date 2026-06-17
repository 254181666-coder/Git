
"""
完整检查4月份数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

print("=== 检查store_daily表4月所有数据 ===\n")
sql = """
SELECT DISTINCT sd.data_date
FROM store_daily sd
WHERE sd.data_date BETWEEN '2026-04-01' AND '2026-04-30'
ORDER BY sd.data_date
"""

df = query(sql)
print("store_daily表中有数据的日期:")
for date in df['data_date']:
    print(f"  - {date}")

print(f"\n\n=== 检查product_sales表4月数据 ===\n")
sql2 = """
SELECT DISTINCT ps.data_date
FROM product_sales ps
WHERE ps.data_date BETWEEN '2026-04-01' AND '2026-04-30'
ORDER BY ps.data_date
"""

df2 = query(sql2)
print("product_sales表中有数据的日期:")
for date in df2['data_date']:
    print(f"  - {date}")

print(f"\n\n=== 检查stored_value表4月数据 ===\n")
sql3 = """
SELECT DISTINCT sv.data_date
FROM stored_value sv
WHERE sv.data_date BETWEEN '2026-04-01' AND '2026-04-30'
ORDER BY sv.data_date
"""

df3 = query(sql3)
print("stored_value表中有数据的日期:")
for date in df3['data_date']:
    print(f"  - {date}")

print(f"\n\n=== 检查store_daily表4月25日具体数据 ===\n")
sql4 = """
SELECT sd.data_date, s.store_name, sd.revenue, sd.customers,
       sd.customers_before_18, sd.customers_18_to_24, sd.customers_after_00
FROM store_daily sd
JOIN stores s ON s.id = sd.store_id
WHERE sd.data_date = '2026-04-25'
ORDER BY s.store_name
"""

df4 = query(sql4)
print(f"4月25日有 {len(df4)} 条store_daily记录:")
print(df4)

print(f"\n\n=== 检查product_sales表4月25日数据 ===\n")
sql5 = """
SELECT * FROM product_sales
WHERE data_date = '2026-04-25'
LIMIT 10
"""

df5 = query(sql5)
print(f"4月25日product_sales有 {len(df5)} 条记录")

