
#!/usr/bin/env python3
"""
验证数据库修复后的最新状态
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("🔍 数据库修复后 - 最新状态验证")
print("=" * 80)

# 1. 检查 order_daily 时段数据（经营总览）
print("\n1️⃣ 【经营总览】时段数据")
sql = """
SELECT time_period, 
       COUNT(*) as order_count, 
       SUM(item_count) as total_items, 
       SUM(revenue) as total_revenue
FROM order_daily
WHERE data_date BETWEEN '2026-04-01' AND '2026-04-30'
  AND order_type IN ('点单', '开放单')
GROUP BY time_period
ORDER BY time_period
"""
df = query(sql)
print(df)

# 2. 检查 order_daily 日期范围
print("\n2️⃣ 【经营总览】日期范围")
sql = """
SELECT MIN(data_date) as min_date, 
       MAX(data_date) as max_date,
       COUNT(*) as total_rows
FROM order_daily
"""
df = query(sql)
print(df)

# 3. 检查 product_sales 表，4月25日数据
print("\n3️⃣ 【商品销售】4月25日数据")
sql = """
SELECT SUM(quantity) as total_quantity, 
       SUM(sales_amount) as total_amount
FROM product_sales
WHERE data_date = '2026-04-25'
"""
df = query(sql)
print(df)

# 4. 检查 product_sales 的品类
print("\n4️⃣ 【商品销售】品类分布")
sql = """
SELECT big_category, 
       COUNT(*) as product_count,
       SUM(quantity) as total_quantity
FROM product_sales
WHERE data_date BETWEEN '2026-04-20' AND '2026-04-30'
GROUP BY big_category
ORDER BY total_quantity DESC
"""
df = query(sql)
print(df)

# 5. 检查 store_daily 日期范围
print("\n5️⃣ 【经营总览】store_daily 日期范围")
sql = """
SELECT MIN(data_date), MAX(data_date), COUNT(*)
FROM store_daily
"""
df = query(sql)
print(df)

print("\n" + "=" * 80)
print("✅ 数据验证完成！现在可以启动看板查看！")
print("=" * 80)
