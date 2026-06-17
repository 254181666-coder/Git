
#!/usr/bin/env python3
"""
检查 product_sales_detail 中的商品名称匹配分类情况
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 product_sales_detail 的商品名称")
print("=" * 80)

sql = """
SELECT product_name, COUNT(*) as count
FROM product_sales_detail
GROUP BY product_name
ORDER BY count DESC
LIMIT 30
"""
df = query(sql)
print(df.to_string())
