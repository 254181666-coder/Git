
"""
检查order_daily表的完整数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 检查order_daily表的time_period数据 ===\n")

sql = """
SELECT DISTINCT time_period, COUNT(*) as count
FROM order_daily
GROUP BY time_period
"""

df = query(sql)
print("各时段的记录数量:")
print(df)

print(f"\n\n=== 检查4月份的完整时段数据 ===\n")
sql2 = """
SELECT od.data_date, od.time_period, 
       SUM(od.item_count) as total_items,
       SUM(od.revenue) as total_revenue
FROM order_daily od
WHERE od.data_date BETWEEN '2026-04-01' AND '2026-04-28'
  AND od.order_type IN ('点单', '开放单')
GROUP BY od.data_date, od.time_period
ORDER BY od.data_date, od.time_period
"""

df2 = query(sql2)
print(f"共 {len(df2)} 条记录，按日期+时段统计:")
print(df2)

print(f"\n\n=== 检查临河街店的数据是否被正确过滤 ===\n")
sql3 = """
SELECT od.store_name, od.time_period,
       SUM(od.item_count) as total_items
FROM order_daily od
WHERE od.order_type IN ('点单', '开放单')
GROUP BY od.store_name, od.time_period
ORDER BY od.store_name, od.time_period
"""

df3 = query(sql3)
print(df3)

