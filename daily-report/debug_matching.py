
#!/usr/bin/env python3
"""
调试订单和套餐的匹配逻辑
"""
import sys
from pathlib import Path

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
print("调试匹配逻辑")
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
    SELECT data_date, store_id, room_no, package, product_name
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单', '开房套餐')
      AND (package LIKE '%%268%%' OR package LIKE '%%团购%%')
""")

print(f"\n通辽团购订单数: {len(od_tongliao)}")
print(f"product_sales_detail相关记录数: {len(psd)}\n")

# 查看(product_sales_detail中)同一个房间同一天是否有多个不同套餐
psd['key'] = psd.apply(lambda x: (x['data_date'], x['store_id'], str(x['room_no'])), axis=1)
multi_pkg = psd.groupby('key').agg({'package': 'nunique'})
multi_pkg = multi_pkg[multi_pkg['package'] > 1]
print(f"同一房间同一天有多个套餐的记录数: {len(multi_pkg)}")

if len(multi_pkg) > 0:
    print("\n【示例】:")
    for key in multi_pkg.head(5).index:
        rows = psd[psd['key'] == key]
        pkgs = rows['package'].unique()
        print(f"\n  {key}有 {len(pkgs)}个套餐:")
        for pkg in pkgs:
            pkg_rows = rows[rows['package'] == pkg]
            print(f"    - {pkg} (商品数: {len(pkg_rows)})")

# 统计一下
print("\n\n【通辽268套餐真正的记录】:")
psd_268 = psd[psd['package'].str.contains('268', na=False)]
print(f"有268的product_sales_detail记录数: {len(psd_268)}")

if len(psd_268) > 0:
    keys_268 = set(psd_268['key'])
    print(f"对应的唯一key数: {len(keys_268)}")
    
    matched_orders = []
    for key in keys_268:
        data_date, store_id, room_no = key
        matches = od_tongliao[
            (od_tongliao['data_date'] == data_date) & 
            (od_tongliao['store_id'] == store_id) & 
            (od_tongliao['room_no'].astype(str) == room_no)
        ]
        for _, order in matches.iterrows():
            matched_orders.append(order)
    
    print(f"匹配到的订单数: {len(matched_orders)}")
    
    if matched_orders:
        df_match = pd.DataFrame(matched_orders)
        print(f"268元的订单数: {len(df_match[df_match['should_amount'] == 268])}")
        print(f"总应收: {df_match['should_amount'].sum():,.2f}")
        print(f"应收分布: {dict(df_match['should_amount'].value_counts())}")
