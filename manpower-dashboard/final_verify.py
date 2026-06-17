
#!/usr/bin/env python3
"""
最终验证所有修复
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("✅ 最终验证 - 检查所有修复是否完成")
print("=" * 80)

print("\n1️⃣ 检查 order_daily 表的时段数据（经营总览）")
sql = """
SELECT time_period, 
       COUNT(*) as order_count, 
       SUM(item_count) as total_items, 
       SUM(revenue) as total_revenue
FROM order_daily
WHERE data_date BETWEEN '2026-04-20' AND '2026-04-22'
  AND order_type IN ('点单', '开放单')
GROUP BY time_period
ORDER BY time_period
"""
df = query(sql)
print(df)

print("\n2️⃣ 检查 product_sales 表，确保没有其他品类")
sql = """
SELECT big_category, 
       COUNT(*) as product_count,
       SUM(quantity) as total_quantity
FROM product_sales
WHERE data_date BETWEEN '2026-04-20' AND '2026-04-22'
GROUP BY big_category
ORDER BY total_quantity DESC
"""
df = query(sql)
print(df)

print("\n3️⃣ 检查 4月25日 product_sales 数据")
sql = """
SELECT SUM(quantity) as total_quantity, 
       SUM(sales_amount) as total_amount
FROM product_sales
WHERE data_date = '2026-04-25'
"""
df = query(sql)
print(df)

print("\n4️⃣ 检查 store_daily 日期范围")
sql = """
SELECT MIN(data_date), MAX(data_date), COUNT(*)
FROM store_daily
"""
df = query(sql)
print(df)

print("\n" + "=" * 80)
print("🎉 所有数据检查完成！")
print("=" * 80)
