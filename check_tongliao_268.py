
#!/usr/bin/env python3
"""
检查通辽268套餐的实际数据 - 找出标准配置
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from collections import Counter

print("=" * 80)
print("检查通辽268套餐标准配置")
print("=" * 80)

sql = """
SELECT 
    s.store_name,
    psd.package,
    psd.room_no,
    psd.product_name,
    psd.quantity,
    psd.sales_amount
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-10'
    AND s.store_name LIKE '%通辽%'
    AND (psd.package LIKE '%268%' OR psd.package LIKE '%团购%')
ORDER BY psd.room_no, psd.product_name
"""

df = query(sql)

if not df.empty:
    print(f"\n共 {len(df)} 条记录\n")
    
    # 按房间号分组查看每个订单的配置
    print("=" * 60)
    print("【1】按房间号查看每个订单的配置")
    print("=" * 60)
    
    for room_no in df['room_no'].unique()[:5]:
        order_df = df[df['room_no'] == room_no]
        pkg = order_df['package'].iloc[0] if len(order_df) > 0 else ''
        store = order_df['store_name'].iloc[0] if len(order_df) > 0 else ''
        
        print(f"\n【{store}】房间: {room_no} | 套餐: {pkg}")
        print("-" * 50)
        
        for _, row in order_df.iterrows():
            print(f"   {row['product_name']:35} | 数量: {row['quantity']:5}")
    
    # 统计每种商品的典型数量
    print("\n\n" + "=" * 60)
    print("【2】分析标准配置（使用众数/中位数）")
    print("=" * 60)
    
    pkg_268 = df[df['package'].str.contains('268', na=False)]
    
    for product_name in pkg_268['product_name'].unique():
        prod_df = pkg_268[pkg_268['product_name'] == product_name]
        quantities = prod_df['quantity'].tolist()
        
        counter = Counter(quantities)
        most_common_qty = counter.most_common(1)[0][0]
        median_qty = sorted(quantities)[len(quantities)//2]
        avg_qty = sum(quantities)/len(quantities)
        
        print(f"\n{product_name}:")
        print(f"   所有订单的数量: {sorted(quantities)}")
        print(f"   众数(最常见): {most_common_qty}")
        print(f"   中位数: {median_qty:.0f}")
        print(f"   平均值: {avg_qty:.1f}")
