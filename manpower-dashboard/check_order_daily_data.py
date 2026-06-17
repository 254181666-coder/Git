
#!/usr/bin/env python3
"""
检查 order_daily 表中的数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 order_daily 表数据")
print("=" * 80)

# 检查一下 order_daily 表有多少数据
sql_count = "SELECT COUNT(*) as total FROM order_daily"
df_count = query(sql_count)
print(f"\norder_daily 表总共有 {df_count['total'].iloc[0]} 条记录")

# 检查一下 order_daily 表的前10条数据
sql = "SELECT * FROM order_daily ORDER BY data_date DESC LIMIT 20"
df = query(sql)
print("\norder_daily 表前20条数据：")
print(df.to_string())

# 按 order_type 统计
print("\n\n按 order_type 统计：")
sql2 = """
    SELECT order_type, COUNT(*) as cnt, SUM(item_count) as total_items, SUM(revenue) as total_revenue
    FROM order_daily
    GROUP BY order_type
"""
df2 = query(sql2)
print(df2.to_string())

# 按日期和时段统计
print("\n\n按日期和时段统计（最近10天）：")
sql3 = """
    SELECT data_date, time_period, COUNT(*) as cnt, SUM(item_count) as items, SUM(revenue) as rev
    FROM order_daily
    WHERE data_date >= '2026-04-20'
    GROUP BY data_date, time_period
    ORDER BY data_date DESC, time_period
"""
df3 = query(sql3)
print(df3.to_string())

print("\n" + "=" * 80)
