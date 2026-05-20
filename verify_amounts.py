#!/usr/bin/env python3
"""
验证团购套餐金额计算
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("验证通辽店 2026-05-08 团购订单金额")
print("=" * 80)

# 查询通辽店的团购订单
sql = """
SELECT od.order_no, od.source_channel, od.actual_amount, od.should_amount, od.room_no
FROM order_detail od
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-08'
  AND s.store_name LIKE '%通辽%'
  AND od.source_channel IN ('抖音', '美团大众', '线下团购')
ORDER BY od.order_no
"""

df_orders = query(sql)
if df_orders.empty:
    print("没有找到订单数据")
    sys.exit(0)

print(f"找到 {len(df_orders)} 个团购订单：")
print(df_orders[['order_no', 'source_channel', 'room_no', 'should_amount', 'actual_amount']].to_string(index=False))

total_actual = df_orders['actual_amount'].sum()
total_should = df_orders['should_amount'].sum()
print(f"\n实收金额合计: {total_actual:,.2f}")
print(f"应收金额合计: {total_should:,.2f}")

print("\n" + "=" * 80)
print("查看美团团购268套餐的统计")
print("=" * 80)

# 统计包含"268"的套餐相关订单
# 通过room_no关联product_sales_detail找到套餐信息
sql = """
SELECT DISTINCT od.order_no, od.room_no, od.actual_amount, psd.package, psd.product_name
FROM order_detail od
LEFT JOIN product_sales_detail psd ON od.store_id = psd.store_id 
                                     AND od.data_date = psd.data_date 
                                     AND od.room_no = psd.room_no
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-08'
  AND s.store_name LIKE '%通辽%'
  AND od.source_channel IN ('抖音', '美团大众', '线下团购')
  AND (psd.package LIKE '%268%' OR psd.package LIKE '%团购%' OR psd.package LIKE '%套餐%')
"""

df_packages = query(sql)
if not df_packages.empty:
    print("\n找到的套餐信息：")
    print(df_packages[['order_no', 'room_no', 'package', 'actual_amount']].to_string(index=False))
    
    # 统计每个套餐的总销售
    pkg_summary = df_packages.groupby('package').agg(
        订单数=('order_no', 'nunique'),
        实收金额=('actual_amount', 'sum')
    ).reset_index()
    print("\n按套餐统计：")
    print(pkg_summary.to_string(index=False))
