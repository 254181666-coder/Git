
#!/usr/bin/env python3
"""
最终调试：直接模拟build_package_stats的逻辑
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

GB_SOURCES = {'抖音', '美团大众', '线下团购'}

def unify(n):
    if not n:
        return None
    return STORE_NAME_MERGE.get(str(n).strip(), str(n).strip())

def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))

print("=" * 80)
print("最终调试：模拟build_package_stats")
print("=" * 80)

sm = store_map()

# 加载数据（和报告脚本一样）
od = query("""
    SELECT store_id, data_date, order_no, open_time, source_channel,
           actual_amount, should_amount, order_type, room_no
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单')
""")

psd = query("""
    SELECT store_id, data_date, room_no, package, product_name,
           quantity, sales_amount
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单', '开房套餐')
      AND (package LIKE '%团购%' OR package LIKE '%套餐%')
""")

if od.empty:
    print("order_detail为空")
    sys.exit()

od['门店'] = od['store_id'].map(sm).apply(unify)
od = od[od['门店'].notna()]
od['is_groupbuy'] = od['source_channel'].isin(GB_SOURCES).astype(int)

if not psd.empty:
    psd['门店'] = psd['store_id'].map(sm).apply(unify)
    psd = psd[psd['门店'].notna()]

# 筛选团购订单
gb_orders = od[od['is_groupbuy'] == 1].copy()
print(f"\n团购订单总数: {len(gb_orders)}")

# 筛选上东的团购订单
shangdong_gb = gb_orders[gb_orders['门店'] == '上东']
print(f"上东团购订单: {len(shangdong_gb)}")

# 获取团购订单的(门店, 房间号)集合
gb_order_keys = set(zip(shangdong_gb['门店'], shangdong_gb['room_no'].fillna('')))
print(f"上东团购订单的(门店,房间号)集合大小: {len(gb_order_keys)}")

# 只筛选属于团购订单的商品明细
psd_gb = psd[psd.apply(lambda x: (x['门店'], str(x['room_no'])) in gb_order_keys, axis=1)]
print(f"上东团购订单关联的商品明细: {len(psd_gb)}")

# 筛选开机套餐
kaiji_pkgs = psd_gb[psd_gb['package'].str.contains('开机套餐$', na=False) & ~psd_gb['package'].str.contains('日场', na=False)]
print(f"\n【开机套餐】(不含日场): {len(kaiji_pkgs)} 条记录")

if not kaiji_pkgs.empty:
    print(f"\n所有(门店,房间号)组合:")
    for (store, room_no), group in kaiji_pkgs.groupby(['门店', 'room_no']):
        pkg_names = group['package'].dropna().unique()
        products = group['product_name'].unique()
        print(f"\n  房间{room_no}: 套餐={pkg_names}")
        print(f"    商品({len(products)}种): {list(products)[:5]}...")
    
    # 统计标准配置
    pkg_product_quantities = {}
    
    for (store, room_no), group in kaiji_pkgs.groupby(['门店', 'room_no']):
        pkg_names = group['package'].dropna().unique()
        if pkg_names.size > 0:
            pkg_name = next((p for p in pkg_names if p), '未知套餐')
            
            key = (store, pkg_name)
            
            if key not in pkg_product_quantities:
                pkg_product_quantities[key] = {}
            
            for product_name in group['product_name'].dropna().unique():
                prod_group = group[group['product_name'] == product_name]
                try:
                    qty_val = prod_group['quantity'].iloc[0]
                except Exception:
                    qty_val = 1
                
                try:
                    qty_int = int(qty_val) if qty_val == int(qty_val) else round(float(qty_val), 1)
                except (ValueError, TypeError):
                    qty_int = round(float(qty_val), 1) if qty_val else 1
                
                if product_name not in pkg_product_quantities[key]:
                    pkg_product_quantities[key][product_name] = []
                pkg_product_quantities[key][product_name].append(qty_int)
    
    print("\n\n>> 标准配置（众数）:")
    for (store, pkg), products in pkg_product_quantities.items():
        result = []
        for product_name, quantities in products.items():
            counter = Counter(quantities)
            most_common_qty = counter.most_common(1)[0][0]
            result.append(f"{product_name}*{most_common_qty}")
        
        result.sort(key=lambda x: x.split('*')[1], reverse=True)
        
        print(f"\n【{pkg}】:")
        print(f"   {', '.join(result[:15])}")
