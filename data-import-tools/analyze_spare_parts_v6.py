#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path

def main():
    # 连接数据库
    conn = pymysql.connect(
        host='localhost', 
        port=3306, 
        user='root', 
        password='CHANGE_ME_MYSQL_PASSWORD', 
        database='ktv_analysis', 
        charset='utf8mb4'
    )

    # 查询所有门店信息
    stores_query = "SELECT id, store_name FROM stores"
    stores_df = pd.read_sql(stores_query, conn)
    
    # 查询2026年6月1日-6月5日各门店的待客量
    customers_query = """
    SELECT 
        store_id,
        SUM(customers) as total_customers
    FROM store_daily
    WHERE data_date >= '2026-06-01' AND data_date <= '2026-06-05'
    GROUP BY store_id
    ORDER BY store_id
    """
    customers_df = pd.read_sql(customers_query, conn)
    customers_df['store_name'] = customers_df['store_id'].map(
        dict(zip(stores_df['id'], stores_df['store_name']))
    )
    
    print("各门店6月1日-6月5日总待客量:")
    print(customers_df)
    print("\n")

    # 建立门店名称到总待客量的映射
    customers_map = {}
    for _, row in customers_df.iterrows():
        key = row['store_name'].replace('店', '')  # 去掉"店"字
        customers_map[key] = row['total_customers']

    # 读取备品统计Excel文件
    file_path = '各店面备品统计.xlsx'
    df_spare = pd.read_excel(file_path, sheet_name='Sheet1', header=None)

    # 找到各门店的出库列位置
    stores_data = {
        '晨宇': 4,
        '上东': 7,
        '榆树': 10,
        '松原一': 13,
        '松原二': 16,
        '通化': 19,
        '鸡西': 22,
        '佳木斯': 25,
        '安达': 28,
        '通辽': 31,
        '红旗街': 34,
        '法库': 37
    }

    # 处理数据，生成新的表格
    results = []
    excluded_keywords = ['打印纸', '小票', 'pos', '三联', 'A4']  # 要排除的打印纸相关关键词
    
    for i in range(3, len(df_spare)):
        row_data = df_spare.iloc[i]
        
        # 检查是否是考核项（第一列不是"不算考核项"或类似说明文字）
        category = row_data[0]
        if pd.notna(category) and isinstance(category, str) and '不算考核' in category:
            continue
        
        product_name = row_data[1]
        unit = row_data[2]
        if pd.isna(product_name):
            continue
        
        # 检查是否是要排除的打印纸相关商品
        product_name_str = str(product_name)
        if any(keyword in product_name_str for keyword in excluded_keywords):
            continue

        # 收集各门店6月1-5日出库量
        store_out_data = {}
        for store_name, col_idx in stores_data.items():
            out_value = row_data[col_idx]
            if pd.isna(out_value):
                out_value = 0
            store_out_data[store_name] = out_value

        results.append({
            'product_name': product_name,
            'unit': unit,
            **store_out_data
        })

    # 生成结果DataFrame
    result_df = pd.DataFrame(results)
    
    # --- 分析不合格商品 ---
    # 先计算各商品在各店的每客消耗量（per_cust_value）
    per_cust_data = []
    for _, row in result_df.iterrows():
        product_dict = {
            'product_name': row['product_name'],
            'unit': row['unit']
        }
        
        # 计算各店每客消耗量
        for store_name in stores_data.keys():
            out_value = row[store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            product_dict[store_name] = per_cust
        
        per_cust_data.append(product_dict)
    
    per_cust_df = pd.DataFrame(per_cust_data)
    
    # 找出不合格商品（低于通辽70%）
    unqualified_by_store = {}
    for store_name in stores_data.keys():
        if store_name == '通辽':  # 跳过通辽自己
            continue
        
        unqualified_items = []
        
        for _, row in per_cust_df.iterrows():
            product_name = row['product_name']
            tongliao_per_cust = row['通辽']
            this_store_per_cust = row[store_name]
            
            # 计算阈值：通辽的70%
            threshold = tongliao_per_cust * 0.7
            
            if this_store_per_cust < threshold and tongliao_per_cust > 0:
                # 计算差距值
                # 差距可以用百分比表示：(标准-实际)/标准 *100
                gap_pct = ((tongliao_per_cust - this_store_per_cust) / tongliao_per_cust) * 100
                # 也可以用实际值差距
                gap_value = tongliao_per_cust - this_store_per_cust
                
                unqualified_items.append({
                    'product_name': product_name,
                    'tongliao_per_cust': tongliao_per_cust,
                    'this_store_per_cust': this_store_per_cust,
                    'threshold': threshold,
                    'gap_pct': gap_pct,
                    'gap_value': gap_value
                })
        
        unqualified_by_store[store_name] = unqualified_items
    
    # 准备HTML表格内容
    html_table_rows = []
    # 表头
    header_cells = ['<th>商品名称</th>', '<th>单位</th>']
    for store_name in stores_data.keys():
        header_cells.append(f'<th>{store_name}出库</th>')
        header_cells.append(f'<th>{store_name}6月1-5日待客量</th>')
        header_cells.append(f'<th>{store_name}每客消耗</th>')
    html_table_rows.append('<tr>' + ''.join(header_cells) + '</tr>')
    
    # 数据行
    for _, row in result_df.iterrows():
        cells = [
            f'<td>{row["product_name"]}</td>',
            f'<td>{row["unit"]}</td>'
        ]
        
        for store_name in stores_data.keys():
            out_value = row[store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            per_cust_pct = f'{per_cust * 100:.2f}%'  # 转换为百分比，保留2位小数
            
            cells.append(f'<td>{int(out_value)}</td>')
            cells.append(f'<td>{int(total_cust)}</td>')
            cells.append(f'<td>{per_cust_pct}</td>')
        
        html_table_rows.append('<tr>' + ''.join(cells) + '</tr>')
    
    # 准备不合格商品HTML部分
    unqualified_html = []
    for store_name, items in unqualified_by_store.items():
        if not items:
            continue
        
        unqualified_html.append(f'<h2 style="margin-top:40px;color:#dc3545;">{store_name} - 不合格商品清单</h2>')
        unqualified_html.append('<table style="width:100%;border-collapse:collapse;margin-top:10px;font-size:14px;">')
        unqualified_html.append('''
            <tr style="background:#dc3545;color:white;">
                <th style="border:1px solid #ddd;padding:10px;text-align:left;">商品名称</th>
                <th style="border:1px solid #ddd;padding:10px;">通辽每客消耗</th>
                <th style="border:1px solid #ddd;padding:10px;">本店每客消耗</th>
                <th style="border:1px solid #ddd;padding:10px;">合格阈值(通辽70%)</th>
                <th style="border:1px solid #ddd;padding:10px;">差距百分比</th>
                <th style="border:1px solid #ddd;padding:10px;">差距值</th>
            </tr>
        ''')
        
        for item in items:
            unqualified_html.append(f'''
                <tr style="background:#fff3cd;">
                    <td style="border:1px solid #ddd;padding:8px;text-align:left;font-weight:500;">{item['product_name']}</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['tongliao_per_cust'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['this_store_per_cust'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['threshold'] * 100:.2f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;color:#dc3545;font-weight:600;">-{item['gap_pct']:.1f}%</td>
                    <td style="border:1px solid #ddd;padding:8px;text-align:center;">{item['gap_value']:.4f}</td>
                </tr>
            ''')
        
        unqualified_html.append('</table>')

    # 生成完整HTML报告
    html_report = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>备品统计-包含6月1-5日待客量与使用占比</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: #f5f7fa;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{ max-width: 1800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; margin-bottom: 20px; text-align: center; }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 20px;
                font-size: 13px;
            }}
            th, td {{ 
                border: 1px solid #e0e0e0; 
                padding: 12px 8px; 
                text-align: center;
            }}
            th {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: 600;
                position: sticky;
                top: 0;
            }}
            tr:nth-child(even) {{ background: #f9f9f9; }}
            tr:hover {{ background: #eef5ff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>备品统计分析（6月1日-6月5日）</h1>
            <p style="text-align:center;margin-bottom:20px;color:#666;">以通辽为标准，低于通辽使用量70%的商品为不合格</p>
            <table>
                {''.join(html_table_rows)}
            </table>
            {''.join(unqualified_html)}
        </div>
    </body>
    </html>
    """
    
    # 保存HTML文件
    html_output_file = Path('report_v3.html')
    with open(html_output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    # 保存Excel文件
    excel_output_file = Path('备品统计_最终版.xlsx')
    
    # 创建用于Excel的DataFrame，包含百分比格式的列
    excel_data = []
    for _, row in result_df.iterrows():
        row_dict = {
            '商品名称': row['product_name'],
            '单位': row['unit']
        }
        
        for store_name in stores_data.keys():
            out_value = row[store_name]
            total_cust = customers_map.get(store_name, 0)
            per_cust = out_value / total_cust if total_cust > 0 else 0
            
            row_dict[f'{store_name}_出库'] = out_value
            row_dict[f'{store_name}_6月1-5日待客量'] = total_cust
            row_dict[f'{store_name}_每客消耗'] = f'{per_cust * 100:.2f}%'
        
        excel_data.append(row_dict)
    
    excel_df = pd.DataFrame(excel_data)
    excel_df.to_excel(excel_output_file, index=False)
    
    print(f"处理完成！最终版报告已保存:")
    print(f"  - {html_output_file}")
    print(f"  - {excel_output_file}")
    
    conn.close()

if __name__ == "__main__":
    main()
