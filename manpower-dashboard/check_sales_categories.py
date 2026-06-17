
#!/usr/bin/env python3
"""
检查各天的商品分类数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查商品分类数据")
print("=" * 80)

dates_to_check = ['2026-04-28', '2026-04-26', '2026-04-25', 
                  '2026-04-24', '2026-04-23']

for date in dates_to_check:
    print(f"\n{'='*80}")
    print(f"日期: {date}")
    print(f"{'='*80}")
    
    sql = f"""
    SELECT big_category, COUNT(*) as count, 
           SUM(quantity) as quantity, SUM(sales_amount) as amount
    FROM product_sales
    WHERE data_date = '{date}'
    GROUP BY big_category
    ORDER BY amount DESC
    """
    df = query(sql)
    print(df.to_string())

print("\n" + "=" * 80)
