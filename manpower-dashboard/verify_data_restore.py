
#!/usr/bin/env python3
"""
验证恢复的数据是否完整
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

# 设置为使用 MySQL
os.environ['USE_MYSQL'] = 'true'

print("=" * 60)
print("验证恢复的数据库数据")
print("=" * 60)

print("\n1. 检查 store_daily 表 (日营业数据)")
sql = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date, COUNT(*) as total_rows
FROM store_daily
"""
df = query(sql)
print(df)

print("\n2. 检查 order_detail 表 (订单明细)")
sql = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date, COUNT(*) as total_rows
FROM order_detail
"""
df = query(sql)
print(df)

print("\n3. 检查 order_detail 表的时段分布 (关键！)")
sql = """
SELECT time_period, COUNT(*) as count
FROM order_detail
WHERE data_date >= '2026-04-20'
GROUP BY time_period
"""
df = query(sql)
print(df)

print("\n4. 检查 product_sales 表 (商品销售)")
sql = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date, COUNT(*) as total_rows
FROM product_sales
"""
df = query(sql)
print(df)

print("\n5. 检查 4月25日 product_sales 数据 (关键！)")
sql = """
SELECT SUM(quantity) as total_quantity, SUM(sales_amount) as total_amount
FROM product_sales
WHERE data_date = '2026-04-25'
"""
df = query(sql)
print(df)

print("\n6. 检查 order_detail 4月20-26日的数据量")
sql = """
SELECT data_date, COUNT(*) as count
FROM order_detail
WHERE data_date BETWEEN '2026-04-20' AND '2026-04-26'
GROUP BY data_date
ORDER BY data_date
"""
df = query(sql)
print(df)

print("\n" + "=" * 60)
