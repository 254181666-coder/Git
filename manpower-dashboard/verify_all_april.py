
#!/usr/bin/env python3
"""
验证 4月份所有日期的数据完整性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("🔍 验证 4月份 order_daily 表所有日期的时段数据")
print("=" * 80)

sql = """
SELECT od.data_date,
       COUNT(DISTINCT od.time_period) as period_count,
       GROUP_CONCAT(DISTINCT od.time_period ORDER BY od.time_period SEPARATOR ', ') as time_periods,
       COUNT(*) as total_orders,
       SUM(od.item_count) as total_items,
       SUM(od.revenue) as total_revenue
FROM order_daily od
WHERE od.order_type IN ('点单', '开放单')
  AND od.data_date BETWEEN '2026-04-01' AND '2026-04-30'
GROUP BY od.data_date
ORDER BY od.data_date DESC
"""
df = query(sql)
print(df)

print("\n" + "=" * 80)
print("✅ 数据验证完成")
print("=" * 80)
