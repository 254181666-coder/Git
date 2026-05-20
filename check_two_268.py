
#!/usr/bin/env python3
"""
检查通辽的两个268套餐 - 为什么一个24瓶，一个2瓶？
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("检查通辽的268套餐详情")
print("=" * 80)

# 查询所有包含268的套餐
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
    AND s.store_name = '通辽'
    AND psd.package LIKE '%268%'
ORDER BY psd.package, psd.room_no, psd.product_name
"""

df = query(sql)

if not df.empty:
    print(f"\n总记录数: {len(df)}")
    
    # 按套餐名分组
    print("\n【所有268套餐名称】")
    for pkg in df['package'].unique():
        count = len(df[df['package'] == pkg])
        print(f"  {pkg}: {count}条")
    
    # 详细查看每个套餐
    for pkg in df['package'].unique():
        pkg_df = df[df['package'] == pkg]
        
        print(f"\n{'='*60}")
        print(f"【{pkg}】")
        print('='*60)
        
        # 按房间号分组
        for room_no in sorted(pkg_df['room_no'].unique())[:5]:
            order_df = pkg_df[pkg_df['room_no'] == room_no]
            date = order_df['data_date'].iloc[0]
            
            print(f"\n房间 {room_no} ({date}):")
            
            beer_qty = 0
            for _, row in order_df.iterrows():
                if '啤酒' in row['product_name'] or '青岛' in row['product_name']:
                    beer_qty += row['quantity']
                    print(f"   ★ {row['product_name']}: {row['quantity']}")
                else:
                    print(f"     {row['product_name']}: {row['quantity']}")
            
            if beer_qty > 0:
                print(f"   >> 啤酒总计: {beer_qty}瓶")
        
        # 统计啤酒总数
        beer_records = pkg_df[pkg_df['product_name'].str.contains('啤酒|青岛', na=False)]
        total_beer = beer_records['quantity'].sum()
        print(f"\n>> 该套餐总啤酒销量: {total_beer}瓶")
