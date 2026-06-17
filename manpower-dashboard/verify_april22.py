
#!/usr/bin/env python3
"""
验证 4月22日数据是否完整
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("🔍 验证 2026-04-22 数据完整性")
print("=" * 80)

# 1. 检查 order_daily 表 2026-04-22 的时段数据
sql = """
SELECT od.data_date, od.time_period,
       COUNT(*) as order_count,
       SUM(od.item_count) as total_items,
       SUM(od.revenue) as total_revenue
FROM order_daily od
WHERE od.data_date = '2026-04-22'
  AND od.order_type IN ('点单', '开放单')
GROUP BY od.data_date, od.time_period
ORDER BY od.time_period
"""
df = query(sql)
print("\n1️⃣ order_daily 表 4月22日时段数据:")
print(df)

# 2. 检查 4月22日是否三个时段都有
sql2 = """
SELECT COUNT(DISTINCT od.time_period) as period_count,
       GROUP_CONCAT(DISTINCT od.time_period ORDER BY od.time_period SEPARATOR ', ') as periods
FROM order_daily od
WHERE od.data_date = '2026-04-22'
  AND od.order_type IN ('点单', '开放单')
"""
df2 = query(sql2)
print("\n2️⃣ 4月22日时段统计:")
print(df2)

# 3. 检查 order_daily 表日期范围
sql3 = """
SELECT MIN(data_date) as min_date,
       MAX(data_date) as max_date
FROM order_daily
"""
df3 = query(sql3)
print("\n3️⃣ order_daily 表日期范围:")
print(df3)

print("\n" + "=" * 80)
print("✅ 验证完成")
print("=" * 80)
