#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path

def main():
    conn = pymysql.connect(
        host='localhost', port=3306, user='root', password='CHANGE_ME_MYSQL_PASSWORD',
        database='ktv_analysis', charset='utf8mb4'
    )

    stores_query = "SELECT id, store_name FROM stores"
    stores_df = pd.read_sql(stores_query, conn)
    
    customers_query = """
    SELECT store_id, SUM(customers) as total_customers
    FROM store_daily
    WHERE data_date >= '2026-06-01' AND data_date <= '2026-06-05'
    GROUP BY store_id ORDER BY store_id
    """
    customers_df = pd.read_sql(customers_query, conn)
    customers_df['store_name'] = customers_df['store_id'].map(
        dict(zip(stores_df['id'], stores_df['store_name']))
    )

    customers_map = {}
    for _, row in customers_df.iterrows():
        key = row['store_name'].replace('店', '')
        customers_map[key] = row['total_customers']

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
        if pd.isna(product_name):
            continue
        product_name_str = str(product_name)
        if any(k in product_name_str for k in excluded_keywords):
            continue
        store_out = {}
        store_in = {}
        for sn, ci in stores_data.items():
            v_out = row_data[ci]
            v_in = row_data[ci - 1]  # 入库列 = 出库列 - 1
            store_out[sn] = 0 if pd.isna(v_out) else int(v_out)
            store_in[sn] = 0 if pd.isna(v_in) else int(v_in)
        note = str(category) if pd.notna(category) else ''
        raw_products.append({
            'product_name': product_name_str,
            'unit': str(unit) if pd.notna(unit) else '',
            'store_out': store_out,
            'store_in': store_in,
            'is_assessment': '不算考核' not in note
        })

    # 合并马桶垫
    m_nw = next((p for p in raw_products if '无纺布' in p['product_name']), None)
    m_sl = next((p for p in raw_products if '溶水型' in p['product_name']), None)
    merged_mattress = None
    if m_nw and m_sl:
        mo = {sn: m_nw['store_out'][sn] + m_sl['store_out'][sn] for sn in stores_data}
        mi = {sn: m_nw['store_in'][sn] + m_sl['store_in'][sn] for sn in stores_data}
        merged_mattress = {'product_name': '一次性马桶垫（合并）', 'unit': '个/片', 'store_out': mo, 'store_in': mi, 'is_assessment': True}

    final_products = []
    mattress_done = False
    for p in raw_products:
        if not p['is_assessment']:
            continue
        if '马桶垫' in p['product_name']:
            if not mattress_done and merged_mattress:
                final_products.append(merged_mattress)
                mattress_done = True
            continue
        final_products.append(p)
    if not mattress_done and merged_mattress:
        final_products.append(merged_mattress)

    final_products = [p for p in final_products if p['store_out']['通辽'] > 0]

    print(f"最终参与考核商品: {len(final_products)} 个\n")

    per_cust = {}
    for p in final_products:
        per_cust[p['product_name']] = {}
        for sn in stores_data:
            cust = customers_map.get(sn, 0)
            per_cust[p['product_name']][sn] = p['store_out'][sn] / cust if cust > 0 else 0

    unqualified = {}
    for sn in stores_data:
        if sn == '通辽': continue
        items = []
        for pn in per_cust:
            tl = per_cust[pn]['通辽']
            ts = per_cust[pn][sn]
            th = tl * 0.7
            # 该店入库为0说明没进货，不算不合格
            store_in_val = next((p['store_in'][sn] for p in final_products if p['product_name'] == pn), 0)
            if ts < th and tl > 0 and store_in_val > 0:
                gap = ((tl - ts) / tl) * 100
                items.append({'product_name': pn, 'tl': tl, 'ts': ts, 'th': th, 'gap': gap})
        unqualified[sn] = items

    store_names = list(stores_data.keys())

    # 待客量汇总行
    cust_cells = ''.join(f'<td>{int(customers_map.get(sn, 0))}</td>' for sn in store_names)

    # 数据行
    data_rows = ''
    for p in final_products:
        cells = f'<td style="text-align:left;">{p["product_name"]}</td><td>{p["unit"]}</td>'
        for sn in store_names:
            o = p['store_out'][sn]
            r = per_cust[p['product_name']][sn]
            if sn == '通辽':
                cells += f'<td><b>{o}</b></td><td><b>{r*100:.2f}%</b></td>'
            else:
                cells += f'<td>{o}</td><td>{r*100:.2f}%</td>'
        data_rows += f'<tr>{cells}</tr>'

    # 不合格汇总
    unq_summary = ''
    for sn in store_names:
        if sn == '通辽': continue
        items = unqualified[sn]
        cnt = len(items)
        names = ', '.join(i['product_name'] for i in items) if items else '—'
        unq_summary += f'<tr><td style="text-align:left;font-weight:600;">{sn}</td><td>{cnt}</td><td style="text-align:left;">{names}</td></tr>'

    # 不合格明细
    unq_detail = ''
    for sn in store_names:
        if sn == '通辽': continue
        items = unqualified[sn]
        if not items: continue
        rows = ''
        for it in items:
            rows += f'<tr><td style="text-align:left;">{it["product_name"]}</td><td>{it["tl"]*100:.2f}%</td><td>{it["ts"]*100:.2f}%</td><td>{it["th"]*100:.2f}%</td><td>-{it["gap"]:.1f}%</td></tr>'
        unq_detail += f'<h3>{sn}</h3><table><tr><th style="text-align:left;">商品</th><th>通辽</th><th>{sn}</th><th>阈值70%</th><th>差距</th></tr>{rows}</table>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>备品考核分析</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333;background:#fff;padding:20px;}}
h1{{font-size:18px;margin-bottom:4px;}}
h2{{font-size:15px;margin:24px 0 12px;}}
h3{{font-size:14px;margin:16px 0 8px;}}
p{{font-size:12px;color:#999;margin-bottom:16px;}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px;}}
th,td{{border:1px solid #ddd;padding:6px 8px;text-align:center;white-space:nowrap;}}
th{{background:#f5f5f5;font-weight:600;}}
tr:hover{{background:#fafafa;}}
</style>
</head>
<body>
<h1>备品考核分析（6.1-6.5）</h1>
<p>标准：通辽（粗体列），低于通辽70%为不合格 | 已排除：不考核项、打印纸、通辽无出库品</p>
<table>
<tr><th>商品</th><th>单位</th>
{''.join(f'<th>{sn}<br>出库</th><th>{sn}<br>消耗率</th>' for sn in store_names)}
</tr>
<tr style="font-size:11px;color:#999;">
<td colspan="2">待客量 →</td>
{cust_cells}
</tr>
{data_rows}
</table>

<h2>不合格商品汇总</h2>
<table>
<tr><th style="text-align:left;">门店</th><th>不合格数</th><th style="text-align:left;">不合格商品</th></tr>
{unq_summary}
</table>
{unq_detail}
</body>
</html>'''

    Path('report.html').write_text(html, encoding='utf-8')

    ed = []
    for p in final_products:
        r = {'商品名称': p['product_name'], '单位': p['unit']}
        for sn in store_names:
            cust = customers_map.get(sn, 0)
            pc = p['store_out'][sn] / cust if cust > 0 else 0
            r[f'{sn}_出库'] = p['store_out'][sn]
            r[f'{sn}_消耗率'] = f'{pc*100:.2f}%'
        ed.append(r)
    pd.DataFrame(ed).to_excel('备品统计_考核版.xlsx', index=False)

    print("完成: report.html / 备品统计_考核版.xlsx")
    conn.close()

if __name__ == "__main__":
    main()
