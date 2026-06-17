#!/usr/bin/env python3
import pymysql
import pandas as pd
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='CHANGE_ME_MYSQL_PASSWORD', 
    database='ktv_analysis', 
    charset='utf8mb4'
)

query = """
SELECT 
    s.store_name,
    YEAR(sd.data_date) as year,
    MONTH(sd.data_date) as month,
    SUM(sd.total_revenue) as total_revenue,
    SUM(sd.actual_amount) as actual_amount,
    SUM(sd.supermarket_revenue) as supermarket_revenue,
    SUM(sd.room_revenue) as room_revenue,
    SUM(sd.stored_card_sales) as stored_card_sales,
    SUM(sd.times_card_sales) as times_card_sales,
    SUM(sd.other_revenue) as other_revenue,
    SUM(sd.online_groupbuy) as online_groupbuy,
    COUNT(*) as days_count
FROM store_daily sd
JOIN stores s ON sd.store_id = s.id
WHERE YEAR(sd.data_date) = 2026
GROUP BY s.store_name, YEAR(sd.data_date), MONTH(sd.data_date)
ORDER BY s.store_name, MONTH(sd.data_date)
"""

df_monthly = pd.read_sql(query, conn)

query_store_total = """
SELECT 
    s.store_name,
    SUM(sd.total_revenue) as total_revenue,
    SUM(sd.actual_amount) as actual_amount,
    SUM(sd.supermarket_revenue) as supermarket_revenue,
    SUM(sd.room_revenue) as room_revenue,
    SUM(sd.stored_card_sales) as stored_card_sales,
    SUM(sd.times_card_sales) as times_card_sales,
    SUM(sd.other_revenue) as other_revenue,
    SUM(sd.online_groupbuy) as online_groupbuy,
    COUNT(DISTINCT sd.data_date) as days_count
FROM store_daily sd
JOIN stores s ON sd.store_id = s.id
WHERE YEAR(sd.data_date) = 2026
GROUP BY s.store_name
ORDER BY total_revenue DESC
"""

df_store_total = pd.read_sql(query_store_total, conn)

query_monthly_stored = """
SELECT 
    s.store_name,
    MONTH(sv.data_date) as month,
    SUM(sv.payment_amount) as stored_sales_amount,
    SUM(sv.stored_amount) as stored_principal,
    COUNT(*) as recharge_count
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE YEAR(sv.data_date) = 2026
GROUP BY s.store_name, MONTH(sv.data_date)
ORDER BY s.store_name, MONTH(sv.data_date)
"""

df_monthly_stored = pd.read_sql(query_monthly_stored, conn)

query_stored_total = """
SELECT 
    s.store_name,
    SUM(sv.payment_amount) as stored_sales_amount,
    SUM(sv.stored_amount) as stored_principal,
    COUNT(*) as recharge_count,
    COUNT(DISTINCT sv.member_phone) as member_count
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE YEAR(sv.data_date) = 2026
GROUP BY s.store_name
ORDER BY stored_sales_amount DESC
"""

df_stored_total = pd.read_sql(query_stored_total, conn)

conn.close()

REPO_DIR = PROJECT_ROOT / "reports"
REPO_DIR.mkdir(exist_ok=True)

total_revenue_all = df_store_total['total_revenue'].sum()
total_stored_all = df_stored_total['stored_sales_amount'].sum()
total_actual_all = df_store_total['actual_amount'].sum()
total_room_all = df_store_total['room_revenue'].sum()
total_supermarket_all = df_store_total['supermarket_revenue'].sum()

store_names = df_store_total['store_name'].tolist()
store_revenue = df_store_total['total_revenue'].tolist()
store_actual = df_store_total['actual_amount'].tolist()
store_stored = df_store_total['stored_card_sales'].tolist()
store_room = df_store_total['room_revenue'].tolist()
store_supermarket = df_store_total['supermarket_revenue'].tolist()

stored_store_names = df_stored_total['store_name'].tolist()
stored_amounts = df_stored_total['stored_sales_amount'].tolist()
stored_principal = df_stored_total['stored_principal'].tolist()
stored_recharge_count = df_stored_total['recharge_count'].tolist()
stored_member_count = df_stored_total['member_count'].tolist()

# 准备月度数据
monthly_revenue_data = {}
monthly_stored_data = {}
for _, row in df_monthly.iterrows():
    store = row['store_name']
    month = int(row['month'])
    if store not in monthly_revenue_data:
        monthly_revenue_data[store] = {}
    monthly_revenue_data[store][month] = {
        'total_revenue': float(row['total_revenue']),
        'stored_card_sales': float(row['stored_card_sales']),
        'actual_amount': float(row['actual_amount'])
    }

for _, row in df_monthly_stored.iterrows():
    store = row['store_name']
    month = int(row['month'])
    if store not in monthly_stored_data:
        monthly_stored_data[store] = {}
    monthly_stored_data[store][month] = {
        'stored_sales_amount': float(row['stored_sales_amount'])
    }

# 准备月度汇总数据
monthly_total_revenue = {}
monthly_total_stored = {}
for month in range(1, 13):
    monthly_total_revenue[month] = 0
    monthly_total_stored[month] = 0

for store in store_names:
    if store in monthly_revenue_data:
        for month in monthly_revenue_data[store]:
            monthly_total_revenue[month] += monthly_revenue_data[store][month]['total_revenue']

for store in stored_store_names:
    if store in monthly_stored_data:
        for month in monthly_stored_data[store]:
            monthly_total_stored[month] += monthly_stored_data[store][month]['stored_sales_amount']

month_labels = ['1月', '2月', '3月', '4月', '5月']
month_revenue_list = [monthly_total_revenue[m] for m in range(1, 6)]
month_stored_list = [monthly_total_stored[m] for m in range(1, 6)]

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026年各店营业额与储值额统计</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #1a1a1a;
            min-height: 100vh;
            padding: 30px 20px;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: #666666;
            font-size: 1.1em;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transition: transform 0.3s;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .card h3 {{
            font-size: 0.9em;
            color: #666666;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .card .value {{
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .card .label {{
            color: #666666;
            font-size: 0.85em;
        }}
        .section {{
            background: #ffffff;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .section h2 {{
            margin-bottom: 25px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.5em;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
        }}
        .table th, .table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        .table th {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            font-weight: 600;
            color: #fff;
        }}
        .table tr:hover {{
            background: #f8f9fa;
        }}
        .table .number {{
            text-align: right;
            font-family: 'SF Mono', 'Consolas', monospace;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: #ffffff;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .chart-container h3 {{
            margin-bottom: 20px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>2026年 各店营业额与储值额统计</h1>
            <p class="subtitle">数据期间: 2026年1月1日 - 5月31日</p>
        </header>

        <div class="dashboard">
            <div class="card">
                <h3>总营业额</h3>
                <div class="value">¥{total_revenue_all:,.0f}</div>
                <div class="label">所有门店合计</div>
            </div>
            <div class="card">
                <h3>总实收金额</h3>
                <div class="value">¥{total_actual_all:,.0f}</div>
                <div class="label">实际收款</div>
            </div>
            <div class="card">
                <h3>总储值额</h3>
                <div class="value">¥{total_stored_all:,.0f}</div>
                <div class="label">储值卡销售</div>
            </div>
            <div class="card">
                <h3>房费收入</h3>
                <div class="value">¥{total_room_all:,.0f}</div>
                <div class="label">包厢房费</div>
            </div>
            <div class="card">
                <h3>超市收入</h3>
                <div class="value">¥{total_supermarket_all:,.0f}</div>
                <div class="label">商品销售</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h3>月度营业额趋势</h3>
                <canvas id="monthlyRevenueChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>月度储值额趋势</h3>
                <canvas id="monthlyStoredChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各店总营业额对比</h3>
                <canvas id="storeRevenueChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各店储值额对比</h3>
                <canvas id="storeStoredChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各店收入构成</h3>
                <canvas id="revenueCompositionChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各店储值笔数与会员数</h3>
                <canvas id="storedCountChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>各店年度汇总</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>门店</th>
                        <th class="number">总营业额</th>
                        <th class="number">实收金额</th>
                        <th class="number">房费收入</th>
                        <th class="number">超市收入</th>
                        <th class="number">储值额</th>
                        <th class="number">次卡销售</th>
                        <th class="number">线上团购</th>
                        <th class="number">营业天数</th>
                    </tr>
                </thead>
                <tbody>
"""

for _, row in df_store_total.iterrows():
    html_content += f"""
                    <tr>
                        <td>{row['store_name']}</td>
                        <td class="number">¥{row['total_revenue']:,.0f}</td>
                        <td class="number">¥{row['actual_amount']:,.0f}</td>
                        <td class="number">¥{row['room_revenue']:,.0f}</td>
                        <td class="number">¥{row['supermarket_revenue']:,.0f}</td>
                        <td class="number">¥{row['stored_card_sales']:,.0f}</td>
                        <td class="number">¥{row['times_card_sales']:,.0f}</td>
                        <td class="number">¥{row['online_groupbuy']:,.0f}</td>
                        <td class="number">{row['days_count']}天</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>各店储值详情</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>门店</th>
                        <th class="number">储值总额</th>
                        <th class="number">储值本金</th>
                        <th class="number">充值笔数</th>
                        <th class="number">会员人数</th>
                        <th class="number">笔均金额</th>
                        <th class="number">人均储值</th>
                    </tr>
                </thead>
                <tbody>
"""

for _, row in df_stored_total.iterrows():
    avg_per_recharge = row['stored_sales_amount'] / row['recharge_count'] if row['recharge_count'] > 0 else 0
    avg_per_member = row['stored_sales_amount'] / row['member_count'] if row['member_count'] > 0 else 0
    html_content += f"""
                    <tr>
                        <td>{row['store_name']}</td>
                        <td class="number">¥{row['stored_sales_amount']:,.0f}</td>
                        <td class="number">¥{row['stored_principal']:,.0f}</td>
                        <td class="number">{row['recharge_count']:,}</td>
                        <td class="number">{row['member_count']:,}</td>
                        <td class="number">¥{avg_per_recharge:,.0f}</td>
                        <td class="number">¥{avg_per_member:,.0f}</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>月度详细数据</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>月份</th>
                        <th class="number">总营业额</th>
                        <th class="number">总储值额</th>
"""

for store in store_names:
    html_content += f"<th class='number'>{store}</th>"

html_content += """
                    </tr>
                </thead>
                <tbody>
"""

for month in range(1, 6):
    month_label = f"{month}月"
    html_content += f"""
                    <tr>
                        <td>{month_label}</td>
                        <td class="number">¥{month_revenue_list[month-1]:,.0f}</td>
                        <td class="number">¥{month_stored_list[month-1]:,.0f}</td>
"""
    
    for store in store_names:
        val = 0
        if store in monthly_revenue_data and month in monthly_revenue_data[store]:
            val = monthly_revenue_data[store][month]['total_revenue']
        html_content += f"<td class='number'>¥{val:,.0f}</td>"
    
    html_content += """
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { labels: { color: '#1a1a1a' } }
            },
            scales: {
                x: { ticks: { color: '#1a1a1a' }, grid: { color: 'rgba(0,0,0,0.05)' } },
                y: { ticks: { color: '#1a1a1a' }, grid: { color: 'rgba(0,0,0,0.05)' } }
            }
        };

        new Chart(document.getElementById('monthlyRevenueChart'), {
            type: 'line',
            data: {
                labels: """ + json.dumps(month_labels) + """,
                datasets: [{
                    label: '营业额',
                    data: """ + json.dumps(month_revenue_list) + """,
                    borderColor: 'rgba(102, 126, 234, 1)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: chartOptions
        });

        new Chart(document.getElementById('monthlyStoredChart'), {
            type: 'line',
            data: {
                labels: """ + json.dumps(month_labels) + """,
                datasets: [{
                    label: '储值额',
                    data: """ + json.dumps(month_stored_list) + """,
                    borderColor: 'rgba(240, 147, 251, 1)',
                    backgroundColor: 'rgba(240, 147, 251, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: chartOptions
        });

        new Chart(document.getElementById('storeRevenueChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [{
                    label: '总营业额',
                    data: """ + json.dumps(store_revenue) + """,
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderWidth: 2
                }]
            },
            options: {
                ...chartOptions,
                indexAxis: 'y'
            }
        });

        new Chart(document.getElementById('storeStoredChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(stored_store_names, ensure_ascii=False) + """,
                datasets: [{
                    label: '储值额',
                    data: """ + json.dumps(stored_amounts) + """,
                    backgroundColor: 'rgba(240, 147, 251, 0.7)',
                    borderWidth: 2
                }]
            },
            options: {
                ...chartOptions,
                indexAxis: 'y'
            }
        });

        new Chart(document.getElementById('revenueCompositionChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [
                    {
                        label: '房费收入',
                        data: """ + json.dumps(store_room) + """,
                        backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    },
                    {
                        label: '超市收入',
                        data: """ + json.dumps(store_supermarket) + """,
                        backgroundColor: 'rgba(240, 147, 251, 0.7)',
                    },
                    {
                        label: '储值额',
                        data: """ + json.dumps(store_stored) + """,
                        backgroundColor: 'rgba(79, 172, 254, 0.7)',
                    }
                ]
            },
            options: {
                ...chartOptions,
                scales: {
                    ...chartOptions.scales,
                    x: { ...chartOptions.scales.x, stacked: true },
                    y: { ...chartOptions.scales.y, stacked: true }
                }
            }
        });

        new Chart(document.getElementById('storedCountChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(stored_store_names, ensure_ascii=False) + """,
                datasets: [
                    {
                        label: '充值笔数',
                        data: """ + json.dumps(stored_recharge_count) + """,
                        backgroundColor: 'rgba(102, 126, 234, 0.7)',
                        yAxisID: 'y'
                    },
                    {
                        label: '会员人数',
                        data: """ + json.dumps(stored_member_count) + """,
                        backgroundColor: 'rgba(245, 87, 108, 0.7)',
                        yAxisID: 'y'
                    }
                ]
            },
            options: chartOptions
        });
    </script>
</body>
</html>
"""

output_file = REPO_DIR / "2026_store_revenue_stored_report.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"\n✅ 2026年各店营业额与储值额报表已生成: {output_file}")
print(f"\n📊 报表摘要:")
print(f"   • 总营业额: ¥{total_revenue_all:,.0f}")
print(f"   • 总实收金额: ¥{total_actual_all:,.0f}")
print(f"   • 总储值额: ¥{total_stored_all:,.0f}")
print(f"   • 房费收入: ¥{total_room_all:,.0f}")
print(f"   • 超市收入: ¥{total_supermarket_all:,.0f}")
print(f"   • 门店数量: {len(df_store_total)}家")

if not df_store_total.empty:
    top_store = df_store_total.iloc[0]
    print(f"   • 营业额最高门店: {top_store['store_name']} (¥{top_store['total_revenue']:,.0f})")

if not df_stored_total.empty:
    top_stored = df_stored_total.iloc[0]
    print(f"   • 储值额最高门店: {top_stored['store_name']} (¥{top_stored['stored_sales_amount']:,.0f})")

print(f"\n📂 请在浏览器中打开查看完整报表")
