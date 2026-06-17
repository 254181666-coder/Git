
"""
检查order_daily表的日期范围
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 检查order_daily表的日期范围 ===\n")

sql = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date
FROM order_daily
"""

df = query(sql)
print(df)

print(f"\n\n=== 检查product_sales表的日期范围 ===\n")
sql2 = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date
FROM product_sales
"""
df2 = query(sql2)
print(df2)

print(f"\n\n=== 检查store_daily表的日期范围 ===\n")
sql3 = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date
FROM store_daily
"""
df3 = query(sql3)
print(df3)

