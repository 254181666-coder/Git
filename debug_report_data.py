
#!/usr/bin/env python3
"""
调试报告生成时的实际数据 - 检查门店名称和套餐名是否正确
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from collections import Counter

STORE_NAME_MERGE = {
    '上东': '上东', '上东店': '上东',
    '临河街': None, '临河街店': None,
    '总部': None, '总部店': None,
    '晨宇': '晨宇', '晨宇店': '晨宇',
    '通辽': '通辽', '通辽店': '通辽',
}

def unify(n):
    if not n:
        return None
    return STORE_NAME_MERGE.get(str(n).strip(), str(n).strip())

def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))

print("=" * 80)
print("调试报告生成时的数据处理")
print("=" * 80)

sm = store_map()

# 模拟报告中的查询
psd = query("""
    SELECT 
        psd.store_id,
        psd.data_date,
        psd.room_no,
        psd.package,
        psd.product_name,
        psd.quantity
    FROM product_sales_detail psd
    WHERE psd.data_date >= '2026-05-01' AND psd.data_date <= '2026-05-10'
      AND (psd.package LIKE '%团购%%' OR psd.package LIKE '%套餐%%')
""")

psd['门店'] = psd['store_id'].map(sm).apply(unify)
psd = psd[psd['门店'].notna()]

print(f"\n处理后的数据: {len(psd)} 条")
print(f"\n门店分布:")
for store in sorted(psd['门店'].unique()):
    count = len(psd[psd['门店'] == store])
    print(f"  {store}: {count}")

# 检查通辽相关数据
tongliao_psd = psd[psd['门店'] == '通辽']
pkg_268_tongliao = tongliao_psd[tongliao_psd['package'].str.contains('268', na=False)]

print(f"\n\n【通辽】268套餐记录: {len(pkg_268_tongliao)}")

if not pkg_268_tongliao.empty:
    # 按房间号分组查看
    for room_no in sorted(pkg_268_tongliao['room_no'].unique())[:3]:
        order_df = pkg_268_tongliao[pkg_268_tongliao['room_no'] == room_no]
        print(f"\n房间 {room_no}:")
        
        for product_name in order_df['product_name'].unique():
            prod_df = order_df[order_df['product_name'] == product_name]
            quantities = prod_df['quantity'].tolist()
            
            counter = Counter(quantities)
            mode_qty = counter.most_common(1)[0][0]
            
            print(f"   {product_name}: 数量列表={quantities}, 众数={mode_qty}")
    
    # 统计所有商品的众数
    print("\n\n【所有商品的众数统计】")
    
    result = {}
    for product_name in pkg_268_tongliao['product_name'].unique():
        prod_df = pkg_268_tongliao[pkg_268_tongliao['product_name'] == product_name]
        quantities = []
        
        # 按房间号分组，每个房间号取一次
        for room_no, group in prod_df.groupby('room_no'):
            qty = group['quantity'].sum() if 'quantity' in group.columns else len(group)
            try:
                qty_int = int(qty) if qty == int(qty) else round(float(qty), 1)
            except:
                qty_int = round(float(qty), 1) if qty else 1
            quantities.append(qty_int)
        
        if not quantities:
            continue
            
        counter = Counter(quantities)
        mode_qty = counter.most_common(1)[0][0]
        result[product_name] = mode_qty
    
    for name, qty in sorted(result.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {qty}")
