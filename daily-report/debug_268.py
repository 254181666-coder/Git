
#!/usr/bin/env python3
"""
调试通辽268套餐 - 查看完整数据分布
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from collections import Counter

print("=" * 80)
print("调试通辽268套餐 - 10天数据")
print("=" * 80)

# 使用和报告相同的日期范围
sql = """
SELECT 
    s.store_name,
    psd.package,
    psd.room_no,
    psd.product_name,
    psd.quantity,
    psd.data_date
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date >= '2026-05-01' AND psd.data_date <= '2026-05-10'
    AND (psd.package LIKE '%268%' OR psd.package LIKE '%团购%')
ORDER BY s.store_name, psd.package, psd.room_no, psd.product_name
"""

df = query(sql)

if not df.empty:
    print(f"总记录数: {len(df)}")
    
    # 筛选通辽268相关套餐
    tongliao = df[df['store_name'].str.contains('通辽', na=False)]
    pkg_268 = tongliao[tongliao['package'].str.contains('268', na=False)]
    
    print(f"\n通辽268套餐记录: {len(pkg_268)}")
    
    if not pkg_268.empty:
        print("\n" + "=" * 60)
        print("【按房间号分组查看每个订单】")
        print("=" * 60)
        
        for room_no in sorted(pkg_268['room_no'].unique()):
            order_df = pkg_268[pkg_268['room_no'] == room_no]
            date = order_df['data_date'].iloc[0]
            pkg = order_df['package'].iloc[0]
            
            print(f"\n房间 {room_no} | 日期:{date} | 套餐:{pkg}")
            for _, row in order_df.iterrows():
                print(f"   {row['product_name']:35} 数量:{row['quantity']:5}")
        
        # 统计每个商品的数量分布
        print("\n\n" + "=" * 60)
        print("【青岛啤酒数量分布】")
        print("=" * 60)
        
        beer = pkg_268[pkg_268['product_name'].str.contains('啤酒|青岛', na=False)]
        
        if not beer.empty:
            qty_list = beer['quantity'].tolist()
            counter = Counter(qty_list)
            
            print(f"\n所有订单中青岛啤酒的数量:")
            for qty, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(qty_list) * 100
                print(f"  {qty}瓶: {count}次 ({pct:.1f}%)")
            
            most_common = counter.most_common(1)[0]
            print(f"\n>>> 众数(最常见): {most_common[0]}瓶 (出现{most_common[1]}次)")
        
        # 所有商品的众数
        print("\n\n" + "=" * 60)
        print("【所有商品的众数（标准配置）】")
        print("=" * 60)
        
        result = []
        for product_name in pkg_268['product_name'].unique():
            prod_df = pkg_268[pkg_268['product_name'] == product_name]
            quantities = prod_df['quantity'].tolist()
            counter = Counter(quantities)
            mode_qty = counter.most_common(1)[0][0]
            result.append((product_name, mode_qty))
        
        # 按数量排序
        result.sort(key=lambda x: x[1], reverse=True)
        
        for name, qty in result:
            print(f"  {name}: {qty}")
