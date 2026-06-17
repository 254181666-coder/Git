#!/usr/bin/env python3
import pymysql, pandas as pd
from pathlib import Path

def main():
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='CHANGE_ME_MYSQL_PASSWORD', database='ktv_analysis', charset='utf8mb4')
    stores_df = pd.read_sql("SELECT id, store_name FROM stores", conn)
    customers_df = pd.read_sql("""
        SELECT store_id, SUM(customers) as total_customers
        FROM store_daily WHERE data_date >= '2026-06-01' AND data_date <= '2026-06-05'
        GROUP BY store_id ORDER BY store_id
    """, conn)
    customers_df['store_name'] = customers_df['store_id'].map(dict(zip(stores_df['id'], stores_df['store_name'])))
    customers_map = {}
    for _, r in customers_df.iterrows():
        customers_map[r['store_name'].replace('店', '')] = r['total_customers']

    df = pd.read_excel('各店面备品统计.xlsx', sheet_name='Sheet1', header=None)

    sd = {
        '晨宇':4,'上东':7,'榆树':10,'松原一':13,'松原二':16,
        '通化':19,'鸡西':22,'佳木斯':25,'安达':28,
        '通辽':31,'红旗街':34,'法库':37
    }
    ex = ['打印纸','小票','pos','三联','A4']
    raw = []
    for i in range(3, len(df)):
        rd = df.iloc[i]
        pn = rd[1]
        if pd.isna(pn): continue
        ps = str(pn)
        if any(k in ps for k in ex): continue
        so, si = {}, {}
        for sn, ci in sd.items():
            so[sn] = 0 if pd.isna(rd[ci]) else int(rd[ci])
            si[sn] = 0 if pd.isna(rd[ci+1]) else int(rd[ci+1])  # 结存列
        note = str(rd[0]) if pd.notna(rd[0]) else ''
        raw.append({'product_name': ps, 'unit': str(rd[2]) if pd.notna(rd[2]) else '', 'store_out': so, 'store_balance': si, 'is_assessment': '不算考核' not in note})

    m_nw = next((p for p in raw if '无纺布' in p['product_name']), None)
    m_sl = next((p for p in raw if '溶水型' in p['product_name']), None)
    merged = None
    if m_nw and m_sl:
        merged = {'product_name': '一次性马桶垫（合并）', 'unit': '个/片',
            'store_out': {sn: m_nw['store_out'][sn]+m_sl['store_out'][sn] for sn in sd},
            'store_balance': {sn: m_nw['store_balance'][sn]+m_sl['store_balance'][sn] for sn in sd},
            'is_assessment': True}

    final = []; done = False
    for p in raw:
        if not p['is_assessment']: continue
        if '马桶垫' in p['product_name']:
            if not done and merged: final.append(merged); done = True
            continue
        final.append(p)
    if not done and merged: final.append(merged)

    # 不再排除通辽无出库品，保留全部
    print(f"考核商品: {len(final)} 个")

    per_cust = {}
    for p in final:
        per_cust[p['product_name']] = {}
        for sn in sd:
            c = customers_map.get(sn, 0)
            per_cust[p['product_name']][sn] = p['store_out'][sn]/c if c>0 else 0

    unqualified = {}
    total_skipped = 0
    for sn in sd:
        if sn == '通辽': continue
        items = []
        skipped = 0
        for p in final:
            pn = p['product_name']
            tl = per_cust[pn]['通辽']
            ts = per_cust[pn][sn]
            sin = p['store_balance'][sn]
            # 结存为0才排出
            if sin == 0:
                skipped += 1
                continue
            th = tl * 0.7
            if ts < th:
                gap = ((tl-ts)/tl)*100 if tl>0 else 0
                items.append({'product_name': pn, 'tl': tl, 'ts': ts, 'th': th, 'gap': gap})
        unqualified[sn] = items
        total_skipped += skipped

    print(f"各店累计跳过(结存=0): {total_skipped} 次")
    total_unq = sum(len(v) for v in unqualified.values())
    print(f"不合格总数: {total_unq}")
    for sn in sd:
        if sn == '通辽': continue
        items = unqualified[sn]
        if items:
            print(f"  {sn}: {len(items)}个 - {', '.join(i['product_name'] for i in items)}")

    sn_list = list(sd.keys())
    cust_cells = ''.join(f'<td>{int(customers_map.get(sn,0))}</td>' for sn in sn_list)
    data_rows = ''
    for p in final:
        cells = f'<td style="text-align:left;">{p["product_name"]}</td><td>{p["unit"]}</td>'
        for sn in sn_list:
            o = p['store_out'][sn]
            r = per_cust[p['product_name']][sn]
            if sn == '通辽':
                cells += f'<td><b>{o}</b></td><td><b>{r*100:.2f}%</b></td>'
            else:
                cells += f'<td>{o}</td><td>{r*100:.2f}%</td>'
        data_rows += f'<tr>{cells}</tr>'

    unq_summary = ''
    for sn in sn_list:
        if sn == '通辽': continue
        items = unqualified[sn]; cnt = len(items)
        names = ', '.join(i['product_name'] for i in items) if items else '—'
        unq_summary += f'<tr><td style="text-align:left;font-weight:600;">{sn}</td><td>{cnt}</td><td style="text-align:left;">{names}</td></tr>'

    unq_detail = ''
    for sn in sn_list:
        if sn == '通辽': continue
        items = unqualified[sn]
        if not items: continue
        rows = ''
        for it in items:
            rows += f'<tr><td style="text-align:left;">{it["product_name"]}</td><td>{it["tl"]*100:.2f}%</td><td>{it["ts"]*100:.2f}%</td><td>{it["th"]*100:.2f}%</td><td>-{it["gap"]:.1f}%</td></tr>'
        unq_detail += f'<h3>{sn}</h3><table><tr><th style="text-align:left;">商品</th><th>通辽</th><th>{sn}</th><th>阈值70%</th><th>差距</th></tr>{rows}</table>'

    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>备品考核分析</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333;background:#fff;padding:20px}}h1{{font-size:18px;margin-bottom:4px}}h2{{font-size:15px;margin:24px 0 12px}}h3{{font-size:14px;margin:16px 0 8px}}p{{font-size:12px;color:#999;margin-bottom:16px}}table{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px}}th,td{{border:1px solid #ddd;padding:6px 8px;text-align:center;white-space:nowrap}}th{{background:#f5f5f5;font-weight:600}}tr:hover{{background:#fafafa}}</style></head><body>
<h1>备品考核分析（6.1-6.5）</h1><p>标准：通辽（粗体），低于通辽70%为不合格 | 排除：不考核项、打印纸、各店结存=0品</p>
<table><tr><th>商品</th><th>单位</th>{''.join(f'<th>{sn}<br>出库</th><th>{sn}<br>消耗率</th>' for sn in sn_list)}</tr>
<tr style="font-size:11px;color:#999;"><td colspan="2">待客量 →</td>{cust_cells}</tr>{data_rows}</table>
<h2>不合格商品汇总</h2><table><tr><th style="text-align:left;">门店</th><th>不合格数</th><th style="text-align:left;">不合格商品</th></tr>{unq_summary}</table>{unq_detail}</body></html>'''

    Path('report.html').write_text(html, encoding='utf-8')
    ed = []
    for p in final:
        r = {'商品名称':p['product_name'],'单位':p['unit']}
        for sn in sn_list:
            c = customers_map.get(sn,0); pc = p['store_out'][sn]/c if c>0 else 0
            r[f'{sn}_出库']=p['store_out'][sn]; r[f'{sn}_消耗率']=f'{pc*100:.2f}%'
        ed.append(r)
    pd.DataFrame(ed).to_excel('备品统计_考核版.xlsx', index=False)
    print("\n完成: report.html")
    conn.close()

if __name__ == "__main__":
    main()
