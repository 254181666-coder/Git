
#!/usr/bin/env python3
"""
检查通辽268套餐的应收金额
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
print("检查通辽268套餐应收金额")
print("=" * 80)

sm = store_map()

# 查询order_detail中通辽的团购订单
od = query("""
    SELECT 
        od.store_id,
        s.store_name,
        od.data_date,
        LEFT(od.order_no, 20) as order_no_short,
        od.source_channel,
        od.actual_amount,
        od.should_amount,
        od.order_type,
        od.room_no,
        psd.package
    FROM order_detail od
    JOIN stores s ON od.store_id = s.id
    LEFT JOIN product_sales_detail psd ON od.data_date = psd.data_date AND od.store_id = psd.store_id AND od.room_no = psd.room_no
    WHERE od.data_date >= '2026-05-01' AND od.data_date <= '2026-05-10'
      AND od.order_type IN ('开房单', '点单')
      AND od.source_channel IN ('抖音', '美团大众', '线下团购')
      AND s.store_name LIKE '%通辽%'
      AND (psd.package LIKE '%268%' OR psd.package LIKE '%团购%')
    ORDER BY od.should_amount DESC
""")

if not od.empty:
    print(f"\n共 {len(od)} 条记录\n")
    
    # 统计
    print("【统计】")
    print(f"订单数: {od['order_no_short'].nunique()}")
    print(f"actual_amount 总计: {od['actual_amount'].sum():,.2f}")
    print(f"should_amount 总计: {od['should_amount'].sum():,.2f}")
    print(f"actual_amount 平均: {od['actual_amount'].mean():,.2f}")
    print(f"should_amount 平均: {od['should_amount'].mean():,.2f}")
    
    # 查看分布
    print("\n\n【should_amount 分布】:")
    for amt in sorted(od['should_amount'].unique())[:20]:
        count = len(od[od['should_amount'] == amt])
        print(f"  {amt:.2f}元: {count}单")
    
    # 显示前20条详细数据
    print("\n\n【详细数据(前20条)】:")
    for _, row in od.head(20).iterrows():
        print(f"{row['data_date']} | 实际:{row['actual_amount']:7.1f} | 应收:{row['should_amount']:7.1f} | 来源:{row['source_channel']:6} | 套餐:{row['package'][:30] if pd.notna(row['package']) else ''}")
