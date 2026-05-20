
#!/usr/bin/env python3
"""
检查store_daily表的数据，并对比order_detail的统计
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from datetime import date

STORE_NAME_MERGE = {
    '上东': '上东', '上东店': '上东',
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
print("对比store_daily和order_detail的数据")
print("=" * 80)

sm = store_map()

# 先看store_daily的数据
print("\n【store_daily表数据】")
sd = query("""
    SELECT store_id, data_date, 
           revenue, total_revenue, actual_amount, online_groupbuy
    FROM store_daily
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
    ORDER BY data_date, store_id
""")

if not sd.empty:
    sd['门店'] = sd['store_id'].map(sm).apply(unify)
    sd = sd[sd['门店'].notna()]
    print(f"有数据的门店: {sd['门店'].nunique()}")
    print(f"\nstore_daily总营收: {sd['actual_amount'].sum():,.2f}")
    print(f"store_daily在线团购: {sd['online_groupbuy'].sum():,.2f}")

    # 按门店汇总
    print("\n【按门店汇总】")
    sd_summary = sd.groupby('门店').agg(
        门店总营收=('actual_amount', 'sum'),
        门店团购营收=('online_groupbuy', 'sum')
    ).reset_index()
    for _, row in sd_summary.iterrows():
        print(f"  {row['门店']}: 总营收 {row['门店总营收']:,.2f}, 团购 {row['门店团购营收']:,.2f}")

# 再看order_detail的数据
print("\n" + "=" * 80)
print("\n【order_detail表数据】")
od = query("""
    SELECT store_id, data_date, actual_amount, should_amount, source_channel
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单')
    ORDER BY data_date, store_id
""")

if not od.empty:
    od['门店'] = od['store_id'].map(sm).apply(unify)
    od = od[od['门店'].notna()]
    od['is_groupbuy'] = od['source_channel'].isin({'抖音', '美团大众', '线下团购'})
    
    print(f"order_detail总营收(actual_amount): {od['actual_amount'].sum():,.2f}")
    gb_od = od[od['is_groupbuy']]
    print(f"order_detail团购营收: {gb_od['actual_amount'].sum():,.2f}")
    
    print(f"\n【对比store_daily和order_detail】")
    print(f"{'':12} {'store_daily':20} {'order_detail':20}")
    print(f"{'':12} {'':20} {'':20}")
    print(f"{'总营收:':12} {sd['actual_amount'].sum():20,.2f} {od['actual_amount'].sum():20,.2f}")
    print(f"{'团购营收:':12} {sd['online_groupbuy'].sum():20,.2f} {gb_od['actual_amount'].sum():20,.2f}")

# 检查为什么有的团购没有商品明细
print("\n" + "=" * 80)
print("\n【为什么有的团购没有商品明细】")
gb_orders = od[od['is_groupbuy']]
print(f"团购订单数: {len(gb_orders)}")

psd = query("""
    SELECT store_id, data_date, room_no, package
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单', '开房套餐')
      AND (package LIKE '%%团购%%' OR package LIKE '%%套餐%%')
""")

if not psd.empty:
    psd['门店'] = psd['store_id'].map(sm).apply(unify)
    psd = psd[psd['门店'].notna()]
    
    # 尝试匹配
    matched_count = 0
    for idx, row in gb_orders.iterrows():
        key = (row['data_date'], row['store_id'], str(row['room_no']) if pd.notna(row['room_no']) else '')
        match = psd[(psd['data_date'] == key[0]) & 
                   (psd['store_id'] == key[1]) & 
                   (psd['room_no'].astype(str) == key[2])]
        if not match.empty:
            matched_count += 1
    
    print(f"有商品明细的订单: {matched_count}")
    print(f"没有商品明细的订单: {len(gb_orders) - matched_count}")
