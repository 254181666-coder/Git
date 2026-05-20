#!/usr/bin/env python3
"""
检查 order_detail 和 product_sales_detail 之间的关联
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("检查 order_detail 表结构")
print("=" * 80)

df_columns = query("SHOW COLUMNS FROM order_detail")
print(df_columns.to_string(index=False))
print("\n")

print("=" * 80)
print("查看通辽店 2026-05-08 一条具体订单的详细信息")
print("=" * 80)

sql = """
SELECT *
FROM order_detail
WHERE data_date = '2026-05-08'
    AND store_id = 6
    AND source_channel IN ('抖音', '美团大众', '线下团购')
ORDER BY id
LIMIT 5
"""

df_orders = query(sql)
if not df_orders.empty:
    print(df_orders.to_string(index=False))
    print("\n")

    # 取一个订单号，看看能否关联到 product_sales_detail
    order_no = df_orders.iloc[0]['order_no']
    print(f"查找订单号 {order_no} 对应的商品明细")
    
    sql2 = f"""
    SELECT *
    FROM product_sales_detail
    WHERE data_date = '2026-05-08'
        AND store_id = 6
        AND room_no = '{df_orders.iloc[0]['room_no']}'
    """
    
    df_products = query(sql2)
    if not df_products.empty:
        print(f"\n找到 {len(df_products)} 条商品明细记录")
        print(df_products[['id', 'room_no', 'package', 'product_name', 'quantity', 'sales_amount']].to_string(index=False))
    else:
        print("\n没有找到对应的商品明细")
