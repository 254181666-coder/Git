
"""
测试4月25日商品数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 测试4月25日product_sales数据 ===\n")

sql = """
    SELECT ps.data_date, ps.product_name, ps.big_category,
           SUM(ps.quantity) as quantity, SUM(ps.sales_amount) as sales_amount
    FROM product_sales ps
    WHERE ps.data_date BETWEEN '2026-04-24' AND '2026-04-26'
    GROUP BY ps.data_date, ps.product_name, ps.big_category
    ORDER BY ps.data_date, quantity DESC
"""

df = query(sql, ('2026-04-24', '2026-04-26'))
print(f"查询结果: {len(df)} 条\n")
print(df.head(10))

print(f"\n--- 按日期汇总 ---\n")
date_summary = df.groupby('data_date').agg({
    'quantity': 'sum', 'sales_amount': 'sum'
}).reset_index()
print(date_summary)

