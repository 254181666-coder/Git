
#!/usr/bin/env python3
"""
检查 order_daily 表中每个日期的时段数据情况
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("📊 检查 order_daily 表 - 每个日期的时段数据")
print("=" * 80)

# 1. 首先按日期和时段汇总数据
sql = """
SELECT od.data_date, 
       od.time_period,
       COUNT(*) as order_count,
       SUM(od.item_count) as total_items,
       SUM(od.revenue) as total_revenue
FROM order_daily od
WHERE od.order_type IN ('点单', '开放单')
  AND od.data_date BETWEEN '2026-04-01' AND '2026-04-30'
GROUP BY od.data_date, od.time_period
ORDER BY od.data_date DESC, od.time_period
"""
df = query(sql)
print(df)

print("\n" + "=" * 80)
print("🔍 检查每个日期有哪些时段")
print("=" * 80)

# 2. 每个日期的时段列表
sql2 = """
SELECT od.data_date,
       GROUP_CONCAT(DISTINCT od.time_period ORDER BY od.time_period SEPARATOR ', ') as time_periods,
       COUNT(DISTINCT od.time_period) as period_count
FROM order_daily od
WHERE od.order_type IN ('点单', '开放单')
  AND od.data_date BETWEEN '2026-04-01' AND '2026-04-30'
GROUP BY od.data_date
ORDER BY od.data_date DESC
"""
df2 = query(sql2)
print(df2)

print("\n" + "=" * 80)
print("✅ 数据检查完成")
print("=" * 80)
