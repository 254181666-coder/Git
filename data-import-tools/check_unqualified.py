#!/usr/bin/env python3
import pymysql
import pandas as pd

conn = pymysql.connect(host='localhost', port=3306, user='root', password='CHANGE_ME_MYSQL_PASSWORD', database='ktv_analysis', charset='utf8mb4')

stores_query = "SELECT id, store_name FROM stores"
stores_df = pd.read_sql(stores_query, conn)

customers_query = """
SELECT store_id, SUM(customers) as total_customers
FROM store_daily
WHERE data_date >= '2026-06-01' AND data_date <= '2026-06-05'
GROUP BY store_id ORDER BY store_id
"""
customers_df = pd.read_sql(customers_query, conn)
customers_df['store_name'] = customers_df['store_id'].map(dict(zip(stores_df['id'], stores_df['store_name'])))

customers_map = {}
for _, row in customers_df.iterrows():
    customers_map[row['store_name'].replace('店', '')] = row['total_customers']

file_path = '各店面备品统计.xlsx'
df_spare = pd.read_excel(file_path, sheet_name='Sheet1', header=None)

stores_data = {
    '晨宇': 4, '上东': 7, '榆树': 10, '松原一': 13, '松原二': 16,
    '通化': 19, '鸡西': 22, '佳木斯': 25, '安达': 28,
    '通辽': 31, '红旗街': 34, '法库': 37
}

excluded_keywords = ['打印纸', '小票', 'pos', '三联', 'A4']
raw_products = []
for i in range(3, len(df_spare)):
    row_data = df_spare.iloc[i]
    category = row_data[0]
    product_name = row_data[1]
    unit = row_data[2]
    if pd.isna(product_name): continue
    product_name_str = str(product_name)
    if any(k in product_name_str for k in excluded_keywords): continue
    store_out, store_in = {}, {}
    for sn, ci in stores_data.items():
        store_out[sn] = 0 if pd.isna(row_data[ci]) else int(row_data[ci])
        store_in[sn] = 0 if pd.isna(row_data[ci-1]) else int(row_data[ci-1])
    note = str(category) if pd.notna(category) else ''
    raw_products.append({
        'product_name': product_name_str,
        'unit': str(unit) if pd.notna(unit) else '',
        'store_out': store_out, 'store_in': store_in,
        'is_assessment': '不算考核' not in note
    })

# 合并马桶垫
m_nw = next((p for p in raw_products if '无纺布' in p['product_name']), None)
m_sl = next((p for p in raw_products if '溶水型' in p['product_name']), None)
merged = None
if m_nw and m_sl:
    merged = {
        'product_name': '一次性马桶垫（合并）', 'unit': '个/片',
        'store_out': {sn: m_nw['store_out'][sn]+m_sl['store_out'][sn] for sn in stores_data},
        'store_in': {sn: m_nw['store_in'][sn]+m_sl['store_in'][sn] for sn in stores_data},
        'is_assessment': True
    }

final = []
done = False
for p in raw_products:
    if not p['is_assessment']: continue
    if '马桶垫' in p['product_name']:
        if not done and merged: final.append(merged); done = True
        continue
    final.append(p)
if not done and merged: final.append(merged)

# 只需通辽有出库
final = [p for p in final if p['store_out']['通辽'] > 0]

print("各店各商品入库情况：")
print(f"{'商品':<20} {'通辽入库':>8}", end='')
for sn in stores_data:
    if sn == '通辽': continue
    print(f' {sn:>6}入库', end='')
print()
for p in final:
    print(f"{p['product_name']:<20} {p['store_in']['通辽']:>8}", end='')
    for sn in stores_data:
        if sn == '通辽': continue
        print(f' {p["store_in"][sn]:>8}', end='')
    print()

print("\n不合格判定明细（入库=0 → 跳过）：")
for sn in stores_data:
    if sn == '通辽': continue
    print(f"\n--- {sn} ---")
    for p in final:
        tl = p['store_out']['通辽'] / customers_map['通辽']
        ts = p['store_out'][sn] / customers_map.get(sn, 1)
        th = tl * 0.7
        sin = p['store_in'][sn]
        is_unq = ts < th and tl > 0 and sin > 0
        skipped = '(跳过,入库=0)' if sin == 0 else ''
        status = '✗不合格' if is_unq else ('✓合格' if sin > 0 else '—')
        print(f"  {p['product_name']:<20} 通辽={tl*100:.2f}%  {sn}={ts*100:.2f}%  阈值={th*100:.2f}%  入库={sin}  {status} {skipped}")

conn.close()
