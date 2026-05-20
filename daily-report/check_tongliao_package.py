#!/usr/bin/env python3
"""
检查通辽268套餐数据
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("查看 product_sales_detail 表结构")
print("=" * 80)

# 查看表结构
df_columns = query("SHOW COLUMNS FROM product_sales_detail")
print(df_columns.to_string(index=False))
print("\n")

print("=" * 80)
print("查询通辽店 2026-05-08 的团购套餐数据")
print("=" * 80)

# 查询通辽店2026-05-08的团购套餐数据
sql = """
SELECT 
    psd.*,
    s.store_name
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-08'
    AND s.store_name LIKE '%通辽%'
    AND (psd.package LIKE '%%团购%%' OR psd.package LIKE '%%套餐%%')
ORDER BY psd.package, psd.id
LIMIT 50
"""

df = query(sql)
if not df.empty:
    print(f"共 {len(df)} 条记录")
    print(df.to_string(index=False))
    
    # 统计套餐销售情况
    print("\n")
    print("=" * 80)
    print("按套餐统计")
    print("=" * 80)
    
    pkg_stats = df.groupby('package').agg(
        总记录数=('id', 'count'),
        数量总和=('quantity', 'sum'),
        销售金额总和=('sales_amount', 'sum'),
        平均单价=('sales_amount', lambda x: x.sum() / df.loc[x.index, 'quantity'].sum())
    ).reset_index()
    
    print(pkg_stats.to_string(index=False))
else:
    print("没有找到数据")

print("\n")
print("=" * 80)
print("查看 order_detail 表中与通辽店相关的团购订单")
print("=" * 80)

sql2 = """
SELECT 
    od.*,
    s.store_name
FROM order_detail od
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-08'
    AND s.store_name LIKE '%通辽%'
    AND od.source_channel IN ('抖音', '美团大众', '线下团购')
ORDER BY od.id
LIMIT 30
"""

df2 = query(sql2)
if not df2.empty:
    print(f"共 {len(df2)} 条订单")
    print(df2[['id', 'order_no', 'source_channel', 'actual_amount', 'order_type']].to_string(index=False))
else:
    print("没有找到数据")
