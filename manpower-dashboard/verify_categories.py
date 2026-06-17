
#!/usr/bin/env python3
"""
验证新表的分类是否正确
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("验证 product_sales_summary 表的分类")
print("=" * 80)

# 检查各日期的分类情况
dates = ['2026-04-28', '2026-04-26', '2026-04-25', '2026-04-24', '2026-04-23', '2026-04-22']

for date in dates:
    print(f"\n日期: {date}")
    print("-" * 80)
    sql = f"""
    SELECT big_category, COUNT(*) as 记录数, 
           SUM(quantity) as 总销量, SUM(sales_amount) as 总金额
    FROM product_sales_summary
    WHERE data_date = '{date}'
    GROUP BY big_category
    ORDER BY 总金额 DESC
    """
    df = query(sql)
    print(df.to_string())

print("\n" + "=" * 80)
print("验证完成！")
