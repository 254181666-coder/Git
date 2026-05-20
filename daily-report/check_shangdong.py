
#!/usr/bin/env python3
"""
直接检查上东开机套餐的数据
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
}

def unify(n):
    if not n:
        return None
    return STORE_NAME_MERGE.get(str(n).strip(), str(n).strip())

def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))

print("=" * 80)
print("检查上东开机套餐")
print("=" * 80)

sm = store_map()

# 查询order_detail中的团购订单
od = query("""
    SELECT store_id, data_date, order_no, open_time, source_channel,
           actual_amount, should_amount, order_type, room_no
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单')
""")

od['门店'] = od['store_id'].map(sm).apply(unify)
od = od[od['门店'].notna()]
od['is_groupbuy'] = od['source_channel'].isin(['抖音', '美团大众', '线下团购']).astype(int)

# 筛选上东的团购订单
shangdong_gb = od[(od['门店'] == '上东') & (od['is_groupbuy'] == 1)]
print(f"\n上东团购订单数: {len(shangdong_gb)}")

if not shangdong_gb.empty:
    print(f"房间号列表: {sorted(shangdong_gb['room_no'].unique())}")

# 查询product_sales_detail
psd = query("""
    SELECT store_id, data_date, room_no, package, product_name,
           quantity, sales_amount
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND (package LIKE '%团购%%' OR package LIKE '%套餐%%')
""")

psd['门店'] = psd['store_id'].map(sm).apply(unify)
psd = psd[psd['门店'].notna()]

# 筛选上东
shangdong_psd = psd[psd['门店'] == '上东']
print(f"\n上东商品明细总数: {len(shangdong_psd)}")

# 找到开机套餐相关的记录
kaiji_pkgs = shangdong_psd[shangdong_psd['package'].str.contains('开机', na=False)]
print(f"\n包含'开机'的套餐记录: {len(kaiji_pkgs)}")

if not kaiji_pkgs.empty:
    print(f"\n【所有开机套餐名称】:")
    for pkg in kaiji_pkgs['package'].unique():
        count = len(kaiji_pkgs[kaiji_pkgs['package'] == pkg])
        print(f"  {pkg}: {count}条")

# 只看团购订单的商品
gb_order_keys = set(zip(shangdong_gb['门店'], shangdong_gb['room_no'].fillna('')))
psd_gb = shangdong_psd[shangdong_psd.apply(lambda x: (x['门店'], str(x['room_no'])) in gb_order_keys, axis=1)]
print(f"\n上东团购订单关联的商品明细: {len(psd_gb)}")

# 筛选开机套餐
kaiji_gb = psd_gb[psd_gb['package'].str.contains('开机', na=False)]
print(f"其中开机套餐: {len(kaiji_gb)}")

if not kaiji_gb.empty:
    # 按套餐名分组，统计每个商品的数量众数
    for pkg_name in kaiji_gb['package'].unique():
        pkg_df = kaiji_gb[kaiji_gb['package'] == pkg_name]
        
        print(f"\n{'='*60}")
        print(f"【{pkg_name}】")
        print('='*60)
        
        result = {}
        for product_name in pkg_df['product_name'].unique():
            prod_df = pkg_df[pkg_df['product_name'] == product_name]
            quantities = []
            
            for room_no, group in prod_df.groupby('room_no'):
                qty = group['quantity'].iloc[0] if len(group) > 0 else 1
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
            
            print(f"  {product_name}: 数量分布={quantities[:5]}... 众数={mode_qty}")
        
        print(f"\n>> 标准配置（按数量排序）:")
        for name, qty in sorted(result.items(), key=lambda x: x[1], reverse=True):
            print(f"   {name}*{qty}")
