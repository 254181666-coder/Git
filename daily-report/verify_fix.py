
#!/usr/bin/env python3
"""
验证修复后的报告数据
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
print("验证修复后的通辽268套餐数据")
print("=" * 80)

# 读取并解析生成的HTML
html_file = PROJECT_ROOT / "data" / "output" / "团购月度报告_2026-05-01_2026-05-10.html"
if html_file.exists():
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # 找到通辽的表格
    import re
    tongliao_match = re.search(r'<h3>通辽</h3><table>(.*?)</table>', html_content, re.DOTALL)
    if tongliao_match:
        table_content = tongliao_match.group(1)
        print(f"找到通辽表格\n")
        
        # 找268套餐的行
        lines = table_content.split('</tr>')
        for line in lines:
            if '268' in line:
                print(f"找到包含268的行:")
                print(line[:300])
                print()

# 直接从数据库验证
sm = store_map()
od = query("""
    SELECT store_id, data_date, room_no, source_channel, actual_amount, should_amount
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单')
      AND source_channel IN ('抖音', '美团大众', '线下团购')
""")
od['门店'] = od['store_id'].map(sm).apply(unify)
od = od[od['门店'] == '通辽']

psd = query("""
    SELECT data_date, store_id, room_no, package
    FROM product_sales_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-10'
      AND order_type IN ('开房单', '点单', '开房套餐')
      AND package LIKE '%%268%%'
""")
psd_tongliao = psd[psd['store_id'].isin(od['store_id'].unique())]

# 建立准确的匹配
tongliao_268_orders = []
for _, order in od.iterrows():
    key = (order['data_date'], order['store_id'], str(order['room_no']))
    match_psd = psd_tongliao[
        (psd_tongliao['data_date'] == order['data_date']) & 
        (psd_tongliao['store_id'] == order['store_id']) & 
        (psd_tongliao['room_no'].astype(str) == str(order['room_no']))
    ]
    if not match_psd.empty:
        tongliao_268_orders.append(order)

if tongliao_268_orders:
    print(f"【验证结果】:")
    print(f"真正268套餐订单数: {len(tongliao_268_orders)}")
    
    df_268 = pd.DataFrame(tongliao_268_orders)
    print(f"总实际金额: {df_268['actual_amount'].sum():,.2f}")
    print(f"总应收金额: {df_268['should_amount'].sum():,.2f}")
    print(f"平均实际金额: {df_268['actual_amount'].mean():,.2f}")
    print(f"平均应收金额: {df_268['should_amount'].mean():,.2f}")
    
    print(f"\n【应收金额分布】:")
    for amt in sorted(df_268['should_amount'].unique()):
        count = len(df_268[df_268['should_amount'] == amt])
        print(f"  {amt:.2f}元: {count}单")
