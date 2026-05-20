
#!/usr/bin/env python3
"""
详细调试268套餐订单匹配过程
"""
import sys
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

STORE_NAME_MERGE = {
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
print("详细调试268套餐匹配过程")
print("=" * 80)

sm = store_map()

# 查询数据
od = query("""
    SELECT store_id, data_date, room_no, source_channel, actual_amount, should_amount
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单')
      AND source_channel IN ('抖音', '美团大众', '线下团购')
""")
od['门店'] = od['store_id'].map(sm).apply(unify)
od_tongliao = od[od['门店'] == '通辽']

psd = query("""
    SELECT data_date, store_id, room_no, package, product_name, quantity
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单', '开房套餐')
      AND (package LIKE '%%268%%' OR package LIKE '%%团购%%')
""")

print(f"通辽团购订单数: {len(od_tongliao)}")
print(f"psd记录数: {len(psd)}")

# 先构建order_to_packages
order_to_packages = {}
for (data_date, store_id, room_no, pkg_name), group in psd.groupby(['data_date', 'store_id', 'room_no', 'package']):
    if pd.isna(pkg_name) or str(pkg_name).strip() == '':
        continue
    key = (data_date, store_id, str(room_no) if pd.notna(room_no) else '')
    if key not in order_to_packages:
        order_to_packages[key] = {}
    order_to_packages[key][pkg_name] = group

# 统计一下
print(f"\n有数据的key数: {len(order_to_packages)}")

# 现在模拟匹配过程，重点看268套餐相关的
print("\n\n【关键调试】:")

stats = {}  # pkg -> list of (actual_amount, should_amount)

for idx, order in od_tongliao.iterrows():
    key = (order['data_date'], order['store_id'], str(order['room_no']))
    
    if key not in order_to_packages:
        continue
    
    pkgs_dict = order_to_packages[key]
    
    if len(pkgs_dict) == 1:
        pkg_name = next(iter(pkgs_dict.keys()))
    else:
        # 多套餐，用价格匹配
        best_match_pkg = None
        best_diff = float('inf')
        for candidate_pkg, _ in pkgs_dict.items():
            numbers = re.findall(r'\d+\.?\d*', candidate_pkg)
            for num_str in numbers:
                try:
                    pkg_price = float(num_str)
                    diff = abs(pkg_price - order['should_amount'])
                    if diff < best_diff:
                        best_diff = diff
                        best_match_pkg = candidate_pkg
                except ValueError:
                    continue
        
        if best_match_pkg:
            pkg_name = best_match_pkg
        else:
            pkg_name = next(iter(pkgs_dict.keys()))
    
    if '268' in pkg_name:
        if pkg_name not in stats:
            stats[pkg_name] = []
        stats[pkg_name].append((order['actual_amount'], order['should_amount']))

print(f"\n匹配到含'268'套餐的订单统计:")
for pkg_name, amounts in stats.items():
    print(f"  {pkg_name}: {len(amounts)}单")
    should_amounts = [a[1] for a in amounts]
    print(f"    应收金额分布:")
    count_dict = pd.Series(should_amounts).value_counts().to_dict()
    for amt, cnt in sorted(count_dict.items()):
        print(f"      {amt:.2f}元: {cnt}单")
    
    total_should = sum(should_amounts)
    print(f"    总应收: {total_should:.2f}")
