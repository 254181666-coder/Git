
#!/usr/bin/env python3
"""
检查最后一周的销量数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 product_sales 表中最后一周的数据")
print("=" * 80)

# 查询最近10天的销量
sql = """
    SELECT ps.data_date, ps.big_category, 
           SUM(ps.quantity) as total_quantity,
           SUM(ps.sales_amount) as total_sales_amount
    FROM product_sales ps
    WHERE ps.data_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
    GROUP BY ps.data_date, ps.big_category
    ORDER BY ps.data_date DESC, total_quantity DESC
"""
df = query(sql)

print("\n最近10天的销量数据：")
print(df.to_string())

print("\n\n按日期统计的总销量：")
sql2 = """
    SELECT ps.data_date,
           SUM(ps.quantity) as total_quantity,
           SUM(ps.sales_amount) as total_sales_amount
    FROM product_sales ps
    WHERE ps.data_date >= DATE_SUB(CURDATE(), INTERVAL 10 DAY)
    GROUP BY ps.data_date
    ORDER BY ps.data_date DESC
"""
df2 = query(sql2)
print(df2.to_string())

print("\n" + "=" * 80)
