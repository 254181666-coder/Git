
"""
检查4月25日的销售数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

print("=== 检查4月25日的product_sales数据...")
print()

sql = """
SELECT ps.data_date, s.store_name, ps.product_name, ps.big_category,
       SUM(ps.quantity) as quantity, SUM(ps.sales_amount) as sales_amount
FROM product_sales ps
JOIN stores s ON ps.store_id = s.id
WHERE ps.data_date = '2026-04-25'
GROUP BY ps.data_date, s.store_name, ps.product_name, ps.big_category
ORDER BY ps.sales_amount DESC
LIMIT 30
"""

df = query(sql)
print("4月25日前30条销售记录:")
print(df)

print(f"\n=== 4月25日各门店销售额汇总 ===")
sql2 = """
SELECT ps.data_date, s.store_name,
       SUM(ps.quantity) as quantity, SUM(ps.sales_amount) as sales_amount
FROM product_sales ps
JOIN stores s ON ps.store_id = s.id
WHERE ps.data_date = '2026-04-25'
GROUP BY ps.data_date, s.store_name
ORDER BY ps.sales_amount DESC
"""

df2 = query(sql2)
print(df2)

print(f"\n=== 4月25日单日汇总 ===")
total = df2['sales_amount'].sum() / 10 if 'sales_amount' in df2.columns else 0
print(f"4月25日总销售额: ¥{total:,.2f}")
print(f"4月25日总销量: {df2['quantity'].sum() if 'quantity' in df2.columns else 0}")

print(f"\n\n=== 其他日期对比（4月20-28日） ===")
sql3 = """
SELECT ps.data_date, SUM(ps.sales_amount) as sales_amount, SUM(ps.quantity) as quantity
FROM product_sales ps
WHERE ps.data_date BETWEEN '2026-04-20' AND '2026-04-28'
GROUP BY ps.data_date
ORDER BY ps.data_date
"""
df3 = query(sql3)
if not df3.empty:
    df3['sales_amount'] = df3['sales_amount'] / 10
    print(df3)

