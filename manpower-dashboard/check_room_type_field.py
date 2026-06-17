
#!/usr/bin/env python3
"""
检查 product_sales_detail 表的字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 product_sales_detail 表的结构")
print("=" * 80)

sql = "DESCRIBE product_sales_detail"
df = query(sql)
print(df.to_string())

print("\n" + "=" * 80)
print("检查 sample 数据")
print("=" * 80)

sql2 = "SELECT * FROM product_sales_detail LIMIT 10"
df2 = query(sql2)
print(df2.to_string())
