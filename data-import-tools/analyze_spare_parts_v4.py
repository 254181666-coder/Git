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
    
    # 现在添加各门店6月1-5日待客量和使用占比列
    for store_name in stores_data.keys():
        # 添加待客量列
        result_df[f'{store_name}_6月1-5日待客量'] = customers_map.get(store_name, 0)
        
        # 计算每客消耗量
        total_cust = customers_map.get(store_name, 0)
        result_df[f'{store_name}_每客消耗量'] = result_df.apply(
            lambda x: x[store_name] / total_cust if total_cust > 0 else 0,
            axis=1
        )

    # 保存结果
    output_file = Path('备品统计_包含6月待客量.xlsx')
    result_df.to_excel(output_file, index=False)
    
    print(f"处理完成！结果已保存到: {output_file}")
    
    # 也同时生成一个HTML格式的报表，方便查看
    html_content = result_df.to_html(
        index=False, 
        float_format=lambda x: f"{x:.6f}" if x < 1 else f"{x:.0f}"
    )

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>备品统计-包含6月1-5日待客量与使用占比</title>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>备品统计-包含6月1-5日待客量与使用占比</h1>
        {html_content}
    </body>
    </html>
    """
    
    with open('备品统计_包含6月待客量.html', 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print(f"HTML报表也已保存: 备品统计_包含6月待客量.html")
    
    conn.close()

if __name__ == "__main__":
    main()
