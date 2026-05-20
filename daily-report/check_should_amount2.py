
#!/usr/bin/env python3
"""
检查通辽268套餐的应收金额 - 简化版
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
        od.room_no
    FROM order_detail od
    JOIN stores s ON od.store_id = s.id
    WHERE od.data_date >= '2026-05-01' AND od.data_date <= '2026-05-10'
      AND od.order_type IN ('开房单', '点单')
      AND od.source_channel IN ('抖音', '美团大众', '线下团购')
      AND s.store_name LIKE '%%通辽%%'
    ORDER BY od.should_amount DESC
""")

if not od.empty:
    print(f"\n通辽团购订单总数: {len(od)}")
    
    # 查询268套餐的房间号
    psd = query("""
        SELECT store_id, data_date, room_no, package
        FROM product_sales_detail
        WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
          AND (package LIKE '%%268%%')
    """)
    
    if not psd.empty:
        tongliao_268_rooms = set(psd[psd['store_id'].isin(od['store_id'].unique())]['room_no'])
        
        # 筛选268套餐的订单
        od_268 = od[od['room_no'].isin(tongliao_268_rooms)]
        
        print(f"268套餐相关订单数: {len(od_268)}")
        
        if not od_268.empty:
            print(f"\n【统计】:")
            print(f"订单数: {len(od_268)}")
            print(f"actual_amount 总计: {od_268['actual_amount'].sum():,.2f}")
            print(f"should_amount 总计: {od_268['should_amount'].sum():,.2f}")
            print(f"actual_amount 平均: {od_268['actual_amount'].mean():,.2f}")
            print(f"should_amount 平均: {od_268['should_amount'].mean():,.2f}")
            
            # 查看分布
            print(f"\n\n【should_amount 分布】:")
            for amt in sorted(od_268['should_amount'].unique())[:20]:
                count = len(od_268[od_268['should_amount'] == amt])
                print(f"  {amt:.2f}元: {count}单")
            
            # 显示前30条详细数据
            print(f"\n\n【详细数据(前30条)】:")
            for _, row in od_268.head(30).iterrows():
                print(f"{row['data_date']} | 实际:{row['actual_amount']:7.1f} | 应收:{row['should_amount']:7.1f} | 来源:{row['source_channel']:6} | 房间:{row['room_no']}")
