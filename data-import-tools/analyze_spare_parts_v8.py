#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path

def main():
    conn = pymysql.connect(
        host='localhost', 
        port=3306, 
        user='root', 
        password='CHANGE_ME_MYSQL_PASSWORD', 
        database='ktv_analysis', 
        charset='utf8mb4'
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
    
    print("各门店6月1日-6月5日总待客量:")
    print(customers_df)
    print()

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
        if any(keyword in product_name_str for keyword in excluded_keywords):
            continue
        
        store_out = {}
        for store_name, col_idx in stores_data.items():
            out_value = row_data[col_idx]
            store_out[store_name] = 0 if pd.isna(out_value) else int(out_value)
        
        note = str(category) if pd.notna(category) else ''
        
        raw_products.append({
            'product_name': product_name_str,
            'unit': str(unit) if pd.notna(unit) else '',
            'store_out': store_out,
            'note': note,
            'is_assessment': '不算考核' not in note
        })
    
    # 合并马桶垫
    mattress_no_woven = None
    mattress_soluble = None
    for p in raw_products:
        if '无纺布' in p['product_name']:
            mattress_no_woven = p
        elif '溶水型' in p['product_name']:
            mattress_soluble = p
    
    merged_mattress = None
    if mattress_no_woven and mattress_soluble:
        merged_out = {}
        for store_name in stores_data.keys():
            merged_out[store_name] = mattress_no_woven['store_out'][store_name] + mattress_soluble['store_out'][store_name]
        merged_mattress = {
            'product_name': '一次性马桶垫（合并）',
            'unit': '个/片',
            'store_out': merged_out,
            'is_assessment': True,
            'note': '无纺布+溶水型合并'
        }
        print("✓ 已合并两种一次性马桶垫\n")
    
    # 构建最终产品列表
    final_products = []
    mattress_merged = False
    
    for p in raw_products:
        if not p['is_assessment']:
            print(f"✗ 排除不考核项: {p['product_name']}")
            continue
        if '马桶垫' in p['product_name']:
            if not mattress_merged and merged_mattress:
                final_products.append(merged_mattress)
                mattress_merged = True
            continue
        final_products.append(p)
    
    if not mattress_merged and merged_mattress:
        final_products.append(merged_mattress)
    
    # --- 排除通辽没有进货的项目 ---
    filtered_products = []
    for p in final_products:
        if p['store_out']['通辽'] == 0:
            print(f"✗ 排除通辽无出库商品: {p['product_name']}")
            continue
        filtered_products.append(p)
    
    final_products = filtered_products
    
    print(f"\n最终参与考核的商品数: {len(final_products)}")
    for i, p in enumerate(final_products):
        print(f"  {i+1}. {p['product_name']} (通辽出库: {p['store_out']['通辽']})")
    print("-" * 50)
    
    # 计算每客消耗量
    per_cust_data = {}
    for p in final_products:
        product_name = p['product_name']
        per_cust_data[product_name] = {}
        for store_name in stores_data.keys():
            out_value = p['store_out'][store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            per_cust_data[product_name][store_name] = per_cust
    
    # 找出不合格商品（低于通辽70%）
    unqualified_by_store = {}
    for store_name in stores_data.keys():
        if store_name == '通辽':
            continue
        unqualified_items = []
        for product_name in per_cust_data:
            tongliao_per_cust = per_cust_data[product_name]['通辽']
            this_store_per_cust = per_cust_data[product_name][store_name]
            threshold = tongliao_per_cust * 0.7
            if this_store_per_cust < threshold and tongliao_per_cust > 0:
                gap_pct = ((tongliao_per_cust - this_store_per_cust) / tongliao_per_cust) * 100
                unqualified_items.append({
                    'product_name': product_name,
                    'tongliao_per_cust': tongliao_per_cust,
                    'this_store_per_cust': this_store_per_cust,
                    'threshold': threshold,
                    'gap_pct': gap_pct
                })
        unqualified_by_store[store_name] = unqualified_items
    
    # --- HTML ---
    html_table_rows = []
    header_cells = ['<th>商品名称</th>', '<th>单位</th>']
    for store_name in stores_data.keys():
        header_cells.append(f'<th>{store_name}出库</th>')
        header_cells.append(f'<th>{store_name}<br>6月1-5日待客量</th>')
        header_cells.append(f'<th>{store_name}<br>每客消耗</th>')
    html_table_rows.append('<tr>' + ''.join(header_cells) + '</tr>')
    
    for p in final_products:
        cells = [
            f'<td style="text-align:left;font-weight:500;">{p["product_name"]}</td>',
            f'<td>{p["unit"]}</td>'
        ]
        for store_name in stores_data.keys():
            out_value = p['store_out'][store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            # 通辽列高亮
            hl = 'style="background:#e8f5e9;font-weight:bold;"' if store_name == '通辽' else ''
            cells.append(f'<td class="number" {hl}>{out_value}</td>')
            cells.append(f'<td class="number">{int(total_cust)}</td>')
            cells.append(f'<td class="number" {hl}>{per_cust * 100:.2f}%</td>')
        html_table_rows.append('<tr>' + ''.join(cells) + '</tr>')
    
    unqualified_html = []
    unqualified_count = {k: len(v) for k, v in unqualified_by_store.items()}
    
    unqualified_html.append('<h2 style="margin-top:50px;color:#333;">各店不合格商品汇总（标准：通辽使用量的70%）</h2>')
    unqualified_html.append('<table style="width:auto;min-width:600px;margin:20px auto;font-size:14px;">')
    unqualified_html.append('<tr style="background:#667eea;color:white;">')
    unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">门店</th>')
    unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">不合格商品数</th>')
    unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">不合格商品</th>')
    unqualified_html.append('</tr>')
    
    for store_name in stores_data.keys():
        if store_name == '通辽':
            continue
        count = unqualified_count.get(store_name, 0)
        item_names = [item['product_name'] for item in unqualified_by_store.get(store_name, [])]
        row_color = '#ffe0e0' if count > 0 else '#e0ffe0'
        unqualified_html.append(f'''
            <tr style="background:{row_color};">
                <td style="border:1px solid #ddd;padding:10px;font-weight:600;">{store_name}</td>
                <td style="border:1px solid #ddd;padding:10px;text-align:center;font-size:20px;font-weight:bold;color:{'#dc3545' if count > 0 else '#28a745'};">{count}</td>
                <td style="border:1px solid #ddd;padding:10px;text-align:left;">{', '.join(item_names) if item_names else '✓ 全部合格'}</td>
            </tr>
        ''')
    unqualified_html.append('</table>')
    
    for store_name in stores_data.keys():
        if store_name == '通辽':
            continue
        items = unqualified_by_store.get(store_name, [])
        if not items:
            continue
        unqualified_html.append(f'<h3 style="margin-top:35px;color:#dc3545;">{store_name} 不合格商品明细</h3>')
        unqualified_html.append('<table style="width:100%;font-size:14px;">')
        unqualified_html.append('<tr style="background:#dc3545;color:white;">')
        unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;text-align:left;">商品名称</th>')
        unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">通辽每客消耗</th>')
        unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">{}每客消耗</th>'.format(store_name))
        unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">合格阈值(通辽70%)</th>')
        unqualified_html.append('<th style="border:1px solid #ddd;padding:10px;">差距百分比</th>')
        unqualified_html.append('</tr>')
        for item in items:
            unqualified_html.append(f'''
                <tr style="background:#fff3cd;">
                    <td style="border:1px solid #ddd;padding:8px;text-align:left;font-weight:500;">{item['product_name']}</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['tongliao_per_cust'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['this_store_per_cust'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['threshold'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;color:#dc3545;font-weight:600;">-{item['gap_pct']:.1f}%</td>
                </tr>
            ''')
        unqualified_html.append('</table>')

    html_report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>备品统计-6月1-5日考核分析</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f5f7fa; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin-bottom: 5px; text-align: center; }}
        h2 {{ color: #333; margin-top: 40px; }}
        h3 {{ margin-top: 30px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 25px; }}
        .note {{ text-align: center; color: #999; font-size: 13px; margin-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 6px; text-align: center; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        tr:hover {{ background: #eef5ff; }}
        .number {{ font-family: 'SF Mono', Consolas, monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>备品统计分析（6月1日 - 6月5日）</h1>
        <p class="subtitle">以通辽为基准，低于通辽使用量70%为不合格</p>
        <p class="note">已排除：不考核项、打印纸类、通辽无出库商品；两种一次性马桶垫已合并</p>
        <table>
            {''.join(html_table_rows)}
        </table>
        {''.join(unqualified_html)}
    </div>
</body>
</html>"""

    html_output_file = Path('report_v5.html')
    with open(html_output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # Excel
    excel_data = []
    for p in final_products:
        row_dict = {'商品名称': p['product_name'], '单位': p['unit']}
        for store_name in stores_data.keys():
            out_value = p['store_out'][store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            row_dict[f'{store_name}_出库'] = out_value
            row_dict[f'{store_name}_6月1-5日待客量'] = int(total_cust)
            row_dict[f'{store_name}_每客消耗'] = f'{per_cust * 100:.2f}%'
        excel_data.append(row_dict)
    
    excel_df = pd.DataFrame(excel_data)
    excel_output_file = Path('备品统计_考核版.xlsx')
    excel_df.to_excel(excel_output_file, index=False)
    
    print(f"\n处理完成！")
    print(f"  HTML: {html_output_file}")
    print(f"  Excel: {excel_output_file}")
    
    conn.close()

if __name__ == "__main__":
    main()
