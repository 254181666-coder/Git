
#!/usr/bin/env python3
"""
验证新表数据是否正常
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("验证 product_sales_summary 表")
print("=" * 80)

# 检查按日期的汇总
sql = """
SELECT data_date, 
       COUNT(*) as 记录数, 
       SUM(quantity) as 总销量, 
       SUM(sales_amount) as 总金额
FROM product_sales_summary
GROUP BY data_date
ORDER BY data_date DESC
"""
df = query(sql)
print(df.to_string())

print("\n" + "=" * 80)
print("验证 product_sales_detail 表")
print("=" * 80)

sql2 = """
SELECT data_date, 
       COUNT(*) as 记录数, 
       SUM(quantity) as 总销量, 
       SUM(sales_amount) as 总金额
FROM product_sales_detail
GROUP BY data_date
ORDER BY data_date DESC
"""
df2 = query(sql2)
print(df2.to_string())

print("\n" + "=" * 80)
print("验证完成！")
