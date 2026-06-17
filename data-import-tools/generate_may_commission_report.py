#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

conn = pymysql.connect(host='localhost', port=3306, user='root', password='CHANGE_ME_MYSQL_PASSWORD', database='ktv_analysis', charset='utf8mb4')

query = """
SELECT 
    s.store_name,
    pc.commission_staff,
    pc.staff_account,
    pc.product,
    pc.quantity,
    pc.commission_amount,
    pc.business_date
FROM product_commission pc
JOIN stores s ON pc.store_id = s.id
WHERE pc.business_date >= '2026-05-01' AND pc.business_date <= '2026-05-31'
"""

df_product = pd.read_sql(query, conn)

query = """
SELECT 
    s.store_name,
    sc.commission_staff,
    sc.staff_account,
    sc.commission_amount,
    sc.business_date
FROM stored_commission sc
JOIN stores s ON sc.store_id = s.id
WHERE sc.business_date >= '2026-05-01' AND sc.business_date <= '2026-05-31'
"""

df_stored = pd.read_sql(query, conn)

query = """
SELECT 
    s.store_name,
    SUM(ps.sales_amount) as product_sales_amount
FROM product_sales_summary ps
JOIN stores s ON ps.store_id = s.id
WHERE ps.data_date >= '2026-05-01' AND ps.data_date <= '2026-05-31'
GROUP BY s.store_name
"""
df_product_sales = pd.read_sql(query, conn)

query = """
SELECT 
    s.store_name,
    SUM(sv.payment_amount) as stored_sales_amount
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE sv.data_date >= '2026-05-01' AND sv.data_date <= '2026-05-31'
GROUP BY s.store_name
"""
df_stored_sales = pd.read_sql(query, conn)

conn.close()

staff_summary = pd.DataFrame()
if not df_product.empty:
    product_summary = df_product.groupby(['store_name', 'commission_staff', 'staff_account']).agg(
        商品提成笔数=('commission_amount', 'count'),
        商品销售数量=('quantity', 'sum'),
        商品提成金额=('commission_amount', 'sum')
    ).reset_index()
    staff_summary = product_summary

if not df_stored.empty:
    stored_summary = df_stored.groupby(['store_name', 'commission_staff', 'staff_account']).agg(
        储值提成笔数=('commission_amount', 'count'),
        储值提成金额=('commission_amount', 'sum')
    ).reset_index()
    
    if staff_summary.empty:
        staff_summary = stored_summary
    else:
        staff_summary = staff_summary.merge(stored_summary, on=['store_name', 'commission_staff', 'staff_account'], how='outer')

staff_summary = staff_summary.fillna(0)
staff_summary['总提成金额'] = staff_summary.get('商品提成金额', 0) + staff_summary.get('储值提成金额', 0)
staff_summary = staff_summary.sort_values(['store_name', '总提成金额'], ascending=[True, False])

product_by_store = df_product.groupby(['store_name', 'product']).agg(
    销售数量=('quantity', 'sum'),
    提成金额=('commission_amount', 'sum')
).reset_index()

product_by_store = product_by_store.sort_values(['store_name', '提成金额'], ascending=[True, False])

top_products = df_product.groupby('product').agg(
    销售数量=('quantity', 'sum'),
    提成金额=('commission_amount', 'sum'),
    提成笔数=('commission_amount', 'count')
).reset_index().sort_values('提成金额', ascending=False)

store_summary = df_product.groupby('store_name').agg(
    商品提成笔数=('commission_amount', 'count'),
    商品提成金额=('commission_amount', 'sum')
).reset_index()

if not df_stored.empty:
    store_stored = df_stored.groupby('store_name').agg(
        储值提成笔数=('commission_amount', 'count'),
        储值提成金额=('commission_amount', 'sum')
    ).reset_index()
    store_summary = store_summary.merge(store_stored, on='store_name', how='outer')
    store_summary = store_summary.fillna(0)
    store_summary['总提成金额'] = store_summary['商品提成金额'] + store_summary['储值提成金额']
    store_summary = store_summary.sort_values('总提成金额', ascending=False)

def calculate_gini(values):
    """计算基尼系数"""
    if len(values) == 0 or values.sum() == 0:
        return 0
    sorted_values = sorted(values)
    n = len(sorted_values)
    cumulative = 0
    weighted_sum = 0
    for i, val in enumerate(sorted_values):
        cumulative += val
        weighted_sum += (i + 1) * val
    return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n

store_details = []
for store_name in staff_summary['store_name'].unique():
    store_data = staff_summary[staff_summary['store_name'] == store_name]
    staff_count = len(store_data)
    commissions = store_data['总提成金额'].values
    
    gini = calculate_gini(commissions)
    
    top5 = store_data.nlargest(5, '总提成金额')
    top5_list = []
    for _, row in top5.iterrows():
        top5_list.append({
            'name': row['commission_staff'],
            'account': row['staff_account'],
            'amount': row['总提成金额']
        })
    
    product_sales_row = df_product_sales[df_product_sales['store_name'] == store_name]
    product_sales_amount = product_sales_row['product_sales_amount'].values[0] if len(product_sales_row) > 0 else 0
    
    stored_sales_row = df_stored_sales[df_stored_sales['store_name'] == store_name]
    stored_sales_amount = stored_sales_row['stored_sales_amount'].values[0] if len(stored_sales_row) > 0 else 0
    
    product_commission = store_data['商品提成金额'].sum() if '商品提成金额' in store_data.columns else 0
    stored_commission = store_data['储值提成金额'].sum() if '储值提成金额' in store_data.columns else 0
    
    product_ratio = (product_commission / product_sales_amount * 100) if product_sales_amount > 0 else 0
    stored_ratio = (stored_commission / stored_sales_amount * 100) if stored_sales_amount > 0 else 0
    
    store_details.append({
        'store_name': store_name,
        'staff_count': staff_count,
        'gini': gini,
        'total_commission': store_data['总提成金额'].sum(),
        'avg_commission': store_data['总提成金额'].mean(),
        'top5': top5_list,
        'product_sales_amount': product_sales_amount,
        'stored_sales_amount': stored_sales_amount,
        'product_commission': product_commission,
        'stored_commission': stored_commission,
        'product_ratio': product_ratio,
        'stored_ratio': stored_ratio
    })

html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026年5月各店员工提成数据分析</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f8f9fa;
            color: #1a1a1a;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
            background: #ffffff;
            border-radius: 20px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #0066cc, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: #666666;
            font-size: 1.1em;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        .card {
            background: #ffffff;
            border-radius: 20px;
            padding: 30px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 {
            font-size: 0.95em;
            color: #666666;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card .value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .card .label {
            color: #666666;
            font-size: 0.9em;
        }
        .section {
            background: #ffffff;
            border-radius: 20px;
            padding: 30px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 30px;
        }
        .section h2 {
            margin-bottom: 25px;
            color: #0066cc;
            font-size: 1.5em;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .table th, .table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        .table th {
            background: #f0f7ff;
            font-weight: 600;
            color: #0066cc;
        }
        .table tr:hover {
            background: #f8f9fa;
        }
        .table .number {
            text-align: right;
            font-family: 'SF Mono', 'Consolas', monospace;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        .chart-container {
            background: #ffffff;
            border-radius: 20px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }
        .chart-container h3 {
            margin-bottom: 20px;
            color: #0066cc;
        }
        .rank {
            display: inline-block;
            width: 24px;
            height: 24px;
            line-height: 24px;
            text-align: center;
            border-radius: 50%;
            font-size: 0.8em;
            font-weight: bold;
        }
        .rank-1 { background: #ffd700; color: #fff; }
        .rank-2 { background: #c0c0c0; color: #fff; }
        .rank-3 { background: #cd7f32; color: #fff; }
        .store-card {
            background: #f8f9fa;
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
        }
        .store-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .store-name {
            font-size: 1.3em;
            font-weight: bold;
            color: #0066cc;
        }
        .store-stats {
            display: flex;
            gap: 20px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-label {
            font-size: 0.8em;
            color: #666666;
            margin-bottom: 5px;
        }
        .stat-value {
            font-size: 1.2em;
            font-weight: bold;
        }
        .gini-high { color: #dc2626; }
        .gini-medium { color: #f59e0b; }
        .gini-low { color: #16a34a; }
        .top5-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .top5-item {
            background: #ffffff;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .top5-rank {
            font-size: 1.5em;
            font-weight: bold;
            color: #666666;
        }
        .top5-info {
            flex: 1;
        }
        .top5-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .top5-amount {
            font-size: 0.9em;
            color: #0066cc;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>2026年5月各店员工提成数据分析</h1>
            <p class="subtitle">数据期间：2026年5月1日 - 5月31日</p>
        </header>
"""

html_content += """
        <div class="section">
            <h2>各门店提成人数与基尼指数</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>门店</th>
                        <th class="number">提成人数</th>
                        <th class="number">总提成金额</th>
                        <th class="number">人均提成</th>
                        <th class="number">基尼指数</th>
                        <th class="number">商品销售总额</th>
                        <th class="number">商品提成/销售</th>
                        <th class="number">储值卡销售总额</th>
                        <th class="number">储值提成/销售</th>
                        <th>收入分配</th>
                    </tr>
                </thead>
                <tbody>
"""

sorted_stores = sorted(store_details, key=lambda x: x['total_commission'], reverse=True)
for idx, store in enumerate(sorted_stores):
    rank = idx + 1
    rank_class = f"rank-{rank}" if rank <= 3 else ""
    rank_display = f'<span class="rank {rank_class}">{rank}</span>' if rank <= 10 else rank
    
    gini = store['gini']
    if gini > 0.4:
        gini_class = 'gini-high'
        gini_label = '差距较大'
    elif gini > 0.3:
        gini_class = 'gini-medium'
        gini_label = '较为均衡'
    else:
        gini_class = 'gini-low'
        gini_label = '非常均衡'
    
    html_content += f"""
                    <tr>
                        <td>{rank_display}</td>
                        <td>{store['store_name']}</td>
                        <td class="number">{store['staff_count']}人</td>
                        <td class="number">¥{store['total_commission']:,.0f}</td>
                        <td class="number">¥{store['avg_commission']:,.0f}</td>
                        <td class="number {gini_class}">{gini:.3f}</td>
                        <td class="number">¥{store['product_sales_amount']:,.0f}</td>
                        <td class="number">{store['product_ratio']:.1f}%</td>
                        <td class="number">¥{store['stored_sales_amount']:,.0f}</td>
                        <td class="number">{store['stored_ratio']:.1f}%</td>
                        <td>{gini_label}</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>
"""

for store in sorted_stores:
    gini = store['gini']
    if gini > 0.4:
        gini_class = 'gini-high'
    elif gini > 0.3:
        gini_class = 'gini-medium'
    else:
        gini_class = 'gini-low'
    
    html_content += f"""
        <div class="store-card">
            <div class="store-header">
                <div class="store-name">{store['store_name']}</div>
                <div class="store-stats">
                    <div class="stat-item">
                        <div class="stat-label">提成人数</div>
                        <div class="stat-value">{store['staff_count']}人</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">总提成</div>
                        <div class="stat-value">¥{store['total_commission']:,.0f}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">人均提成</div>
                        <div class="stat-value">¥{store['avg_commission']:,.0f}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">基尼指数</div>
                        <div class="stat-value {gini_class}">{gini:.3f}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">商品销售</div>
                        <div class="stat-value">¥{store['product_sales_amount']:,.0f}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">储值卡销售</div>
                        <div class="stat-value">¥{store['stored_sales_amount']:,.0f}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">商品提成占比</div>
                        <div class="stat-value">{store['product_ratio']:.1f}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">储值提成占比</div>
                        <div class="stat-value">{store['stored_ratio']:.1f}%</div>
                    </div>
                </div>
            </div>
            <div>
                <h4 style="margin-bottom: 15px; color: #666666;">TOP5 提成员工</h4>
                <div class="top5-list">
"""
    
    for i, top in enumerate(store['top5']):
        rank_display = i + 1
        html_content += f"""
                    <div class="top5-item">
                        <div class="top5-rank">{rank_display}</div>
                        <div class="top5-info">
                            <div class="top5-name">{top['name']}</div>
                            <div class="top5-amount">¥{top['amount']:,.0f}</div>
                        </div>
                    </div>
"""
    
    html_content += """
                </div>
            </div>
        </div>
"""

total_commission = staff_summary['总提成金额'].sum() if not staff_summary.empty else 0
total_staff = staff_summary['commission_staff'].nunique() if not staff_summary.empty else 0
total_stores = staff_summary['store_name'].nunique() if not staff_summary.empty else 0
avg_commission = total_commission / total_staff if total_staff > 0 else 0

html_content += f"""
        <div class="dashboard">
            <div class="card">
                <h3>总提成金额</h3>
                <div class="value">¥{total_commission:,.0f}</div>
                <div class="label">5月全店合计</div>
            </div>
            <div class="card">
                <h3>参与提成员工</h3>
                <div class="value">{total_staff}</div>
                <div class="label">人</div>
            </div>
            <div class="card">
                <h3>门店数量</h3>
                <div class="value">{total_stores}</div>
                <div class="label">家</div>
            </div>
            <div class="card">
                <h3>人均提成</h3>
                <div class="value">¥{avg_commission:,.0f}</div>
                <div class="label">元/人</div>
            </div>
        </div>
"""

if not store_summary.empty:
    html_content += """
        <div class="section">
            <h2>各门店提成汇总</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>门店</th>
                        <th class="number">商品提成笔数</th>
                        <th class="number">商品提成金额</th>
                        <th class="number">储值提成笔数</th>
                        <th class="number">储值提成金额</th>
                        <th class="number">总提成金额</th>
                    </tr>
                </thead>
                <tbody>
"""
    for idx, row in store_summary.iterrows():
        rank = idx + 1
        rank_class = f"rank-{rank}" if rank <= 3 else ""
        rank_display = f'<span class="rank {rank_class}">{rank}</span>' if rank <= 10 else rank
        html_content += f"""
                    <tr>
                        <td>{rank_display}</td>
                        <td>{row['store_name']}</td>
                        <td class="number">{int(row.get('商品提成笔数', 0)):,}</td>
                        <td class="number">¥{row.get('商品提成金额', 0):,.0f}</td>
                        <td class="number">{int(row.get('储值提成笔数', 0)):,}</td>
                        <td class="number">¥{row.get('储值提成金额', 0):,.0f}</td>
                        <td class="number" style="font-weight:bold">¥{row['总提成金额']:,.0f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

if not staff_summary.empty:
    html_content += """
        <div class="section">
            <h2>各店员工提成明细</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>门店</th>
                        <th>员工姓名</th>
                        <th>员工账号</th>
                        <th class="number">商品提成笔数</th>
                        <th class="number">商品销售数量</th>
                        <th class="number">商品提成金额</th>
                        <th class="number">储值提成笔数</th>
                        <th class="number">储值提成金额</th>
                        <th class="number">总提成金额</th>
                    </tr>
                </thead>
                <tbody>
"""
    for _, row in staff_summary.iterrows():
        html_content += f"""
                    <tr>
                        <td>{row['store_name']}</td>
                        <td>{row['commission_staff']}</td>
                        <td>{row['staff_account']}</td>
                        <td class="number">{int(row.get('商品提成笔数', 0)):,}</td>
                        <td class="number">{int(row.get('商品销售数量', 0)):,}</td>
                        <td class="number">¥{row.get('商品提成金额', 0):,.0f}</td>
                        <td class="number">{int(row.get('储值提成笔数', 0)):,}</td>
                        <td class="number">¥{row.get('储值提成金额', 0):,.0f}</td>
                        <td class="number" style="font-weight:bold">¥{row['总提成金额']:,.0f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

if not top_products.empty:
    html_content += """
        <div class="section">
            <h2>提成商品TOP20</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>商品名称</th>
                        <th class="number">提成笔数</th>
                        <th class="number">销售数量</th>
                        <th class="number">提成金额</th>
                    </tr>
                </thead>
                <tbody>
"""
    for idx, row in top_products.head(20).iterrows():
        rank = idx + 1
        rank_class = f"rank-{rank}" if rank <= 3 else ""
        rank_display = f'<span class="rank {rank_class}">{rank}</span>'
        html_content += f"""
                    <tr>
                        <td>{rank_display}</td>
                        <td>{row['product']}</td>
                        <td class="number">{int(row['提成笔数']):,}</td>
                        <td class="number">{int(row['销售数量']):,}</td>
                        <td class="number">¥{row['提成金额']:,.0f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

html_content += """
        <div class="charts-grid">
            <div class="chart-container">
                <h3>各门店总提成金额对比</h3>
                <canvas id="storeChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>商品提成 vs 储值提成占比</h3>
                <canvas id="typeChart"></canvas>
            </div>
        </div>
"""

if not store_summary.empty:
    store_labels = store_summary['store_name'].tolist()
    store_values = store_summary['总提成金额'].tolist()
    product_values = store_summary.get('商品提成金额', pd.Series([0]*len(store_summary))).tolist()
    stored_values = store_summary.get('储值提成金额', pd.Series([0]*len(store_summary))).tolist()
    
    total_product = sum(product_values)
    total_stored = sum(stored_values)

    html_content += f"""
        <script>
            const chartOptions = {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ labels: {{ color: '#1a1a1a' }} }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#1a1a1a' }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
                    y: {{ ticks: {{ color: '#1a1a1a' }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
                }}
            }};

            new Chart(document.getElementById('storeChart'), {{
                type: 'bar',
                data: {{
                    labels: {store_labels},
                    datasets: [{{
                        label: '总提成金额',
                        data: {store_values},
                        backgroundColor: [
                            'rgba(0,102,204,0.7)',
                            'rgba(234,88,12,0.7)',
                            'rgba(124,58,237,0.7)',
                            'rgba(22,163,74,0.7)',
                            'rgba(220,38,38,0.7)',
                            'rgba(245,158,11,0.7)',
                            'rgba(107,114,128,0.7)'
                        ],
                        borderWidth: 2
                    }}]
                }},
                options: chartOptions
            }});

            new Chart(document.getElementById('typeChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ['商品提成', '储值提成'],
                    datasets: [{{
                        data: [{total_product}, {total_stored}],
                        backgroundColor: ['rgba(0,102,204,0.7)', 'rgba(234,88,12,0.7)'],
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{ labels: {{ color: '#1a1a1a' }} }}
                    }}
                }}
            }});
        </script>
"""

html_content += """
    </div>
</body>
</html>
"""

output_file = REPORTS_DIR / "may_2026_staff_commission_analysis.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"\n✅ 5月份员工提成数据分析报告已生成: {output_file}")
print(f"\n📊 报告摘要:")
print(f"   • 总提成金额: ¥{total_commission:,.0f}")
print(f"   • 参与提成员工: {total_staff}人")
print(f"   • 门店数量: {total_stores}家")
print(f"   • 人均提成: ¥{avg_commission:,.0f}")
if not store_summary.empty:
    top_store = store_summary.iloc[0]
    print(f"   • 提成最高门店: {top_store['store_name']} (¥{top_store['总提成金额']:,.0f})")
if not staff_summary.empty:
    top_staff = staff_summary.loc[staff_summary['总提成金额'].idxmax()]
    print(f"   • 提成最高员工: {top_staff['commission_staff']} ({top_staff['store_name']}) ¥{top_staff['总提成金额']:,.0f}")
print(f"\n📂 请在浏览器中打开查看完整报告")
