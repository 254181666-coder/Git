
#!/usr/bin/env python3
"""
检查 product_sales 表的销量数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 product_sales 表数据")
print("=" * 80)

# 检查 product_sales 表的数据总量
sql1 = "SELECT COUNT(*) as total FROM product_sales"
df1 = query(sql1)
print(f"\nproduct_sales 表共有 {df1['total'].iloc[0]} 条记录")

# 检查最近几天的销量
sql2 = """
    SELECT data_date, SUM(quantity) as total_quantity, SUM(sales_amount) as total_amount
    FROM product_sales
    WHERE data_date >= '2026-04-20'
    GROUP BY data_date
    ORDER BY data_date DESC
"""
df2 = query(sql2)
print("\n最近几天销量：")
print(df2.to_string())

# 检查商品分类销量
sql3 = """
    SELECT big_category, SUM(quantity) as total_quantity, SUM(sales_amount) as total_amount
    FROM product_sales
    WHERE data_date >= '2026-04-20'
    GROUP BY big_category
    ORDER BY total_quantity DESC
"""
df3 = query(sql3)
print("\n商品分类销量：")
print(df3.to_string())

print("\n" + "=" * 80)
