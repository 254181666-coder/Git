#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, date
import pymysql
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)

# 获取临河街店的ID
cursor = conn.cursor()
cursor.execute("SELECT id FROM stores WHERE store_name = '临河街店'")
store_id = cursor.fetchone()[0]
cursor.close()

# 获取最新数据日期
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT MAX(data_date) as max_date FROM store_daily WHERE store_id = %s", (store_id,))
max_date_result = cursor.fetchone()
report_date = max_date_result['max_date'] or date.today()
cursor.close()

# 获取日营业数据
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT * FROM store_daily WHERE store_id = %s AND data_date = %s", (store_id, report_date))
daily_data = cursor.fetchone()
cursor.close()

# 获取商品销售数据（按大类别汇总）
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("""
    SELECT big_category, SUM(quantity) as total_quantity, SUM(sales_amount) as total_amount
    FROM product_sales
    WHERE store_id = %s AND data_date = %s
    GROUP BY big_category
    ORDER BY total_amount DESC
""", (store_id, report_date))
product_summary = cursor.fetchall()
cursor.close()

# 获取商品销售明细（前20名）
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("""
    SELECT product_name, category, SUM(quantity) as total_quantity, SUM(sales_amount) as total_amount
    FROM product_sales
    WHERE store_id = %s AND data_date = %s
    GROUP BY product_name, category
    ORDER BY total_amount DESC
    LIMIT 20
""", (store_id, report_date))
product_detail = cursor.fetchall()
cursor.close()

# 获取订单明细
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("""
    SELECT * FROM order_detail
    WHERE store_id = %s AND data_date = %s
    ORDER BY open_time
""", (store_id, report_date))
orders = cursor.fetchall()
cursor.close()

# 获取时段分析
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("""
    SELECT time_period, COUNT(*) as order_count, SUM(actual_amount) as total_amount, AVG(actual_amount) as avg_amount
    FROM order_detail
    WHERE store_id = %s AND data_date = %s
    GROUP BY time_period
""", (store_id, report_date))
time_period_analysis = cursor.fetchall()
cursor.close()

conn.close()

# 生成HTML报告
html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>临河街店 - 日报</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff; min-height: 100vh; padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center; padding: 40px 20px; margin-bottom: 40px;
            background: rgba(255,255,255,0.05); border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            font-size: 2.5em; margin-bottom: 10px;
            background: linear-gradient(45deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .dashboard {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px; margin-bottom: 40px;
        }
        .card {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1); transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 {
            font-size: 0.9em; color: #a0a0a0; margin-bottom: 15px;
            text-transform: uppercase; letter-spacing: 1px;
        }
        .card .value { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
        .section {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;
        }
        .section h2 { margin-bottom: 25px; color: #00d4ff; }
        .table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        .table th, .table td {
            padding: 12px 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .table th {
            background: rgba(0,0,0,0.2); font-weight: 600; color: #00d4ff;
        }
        .table tr:hover { background: rgba(255,255,255,0.05); }
        .charts-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px; margin-bottom: 30px;
        }
        .chart-container {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .chart-container h3 { margin-bottom: 20px; color: #00d4ff; }
        .positive { color: #4ade80; }
        .negative { color: #ef4444; }
        .highlight { color: #ffd700; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>临河街店 - 日报</h1>
            <p style="color:#a0a0a0; font-size:1.1em">""" + str(report_date) + """</p>
        </header>
"""

# 日营业数据卡片
if daily_data:
    html_content += """
        <div class="dashboard">
            <div class="card">
                <h3>总计营业额</h3>
                <div class="value" style="color:#00d4ff">¥""" + f"{float(daily_data['total_revenue']):,.2f}" + """</div>
            </div>
            <div class="card">
                <h3>实收金额</h3>
                <div class="value" style="color:#7b2cbf">¥""" + f"{float(daily_data['actual_amount']):,.2f}" + """</div>
            </div>
            <div class="card">
                <h3>超市收入</h3>
                <div class="value" style="color:#4ade80">¥""" + f"{float(daily_data['supermarket_revenue']):,.2f}" + """</div>
            </div>
            <div class="card">
                <h3>房费收入</h3>
                <div class="value" style="color:#fb923c">¥""" + f"{float(daily_data['room_revenue']):,.2f}" + """</div>
            </div>
            <div class="card">
                <h3>储值卡销售</h3>
                <div class="value" style="color:#a78bfa">¥""" + f"{float(daily_data['stored_card_sales']):,.2f}" + """</div>
            </div>
            <div class="card">
                <h3>全天待客台数</h3>
                <div class="value" style="color:#f472b6">""" + str(daily_data['customers']) + """</div>
            </div>
        </div>
"""

# 商品销售汇总
if product_summary:
    html_content += """
        <div class="section">
            <h2>商品销售汇总（按大类）</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>大类</th><th>销售数量</th><th>销售金额</th><th>占比</th>
                    </tr>
                </thead>
                <tbody>
"""
    total_product_amount = sum(float(p['total_amount']) for p in product_summary)
    for p in product_summary:
        percentage = (float(p['total_amount']) / total_product_amount * 100) if total_product_amount > 0 else 0
        html_content += f"""
                    <tr>
                        <td>{p['big_category']}</td>
                        <td>{p['total_quantity']}</td>
                        <td>¥{float(p['total_amount']):,.2f}</td>
                        <td>{percentage:.1f}%</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

# 商品销售明细Top20
if product_detail:
    html_content += """
        <div class="section">
            <h2>商品销售明细 Top20</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>排名</th><th>商品名称</th><th>类别</th><th>销售数量</th><th>销售金额</th>
                    </tr>
                </thead>
                <tbody>
"""
    for idx, p in enumerate(product_detail, 1):
        html_content += f"""
                    <tr>
                        <td>{idx}</td>
                        <td>{p['product_name']}</td>
                        <td>{p['category']}</td>
                        <td>{p['total_quantity']}</td>
                        <td>¥{float(p['total_amount']):,.2f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

# 时段分析
if time_period_analysis:
    html_content += """
        <div class="charts-grid">
            <div class="chart-container">
                <h3>时段分析 - 订单数</h3>
                <canvas id="periodOrdersChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>时段分析 - 销售额</h3>
                <canvas id="periodAmountChart"></canvas>
            </div>
        </div>
        <div class="section">
            <h2>时段分析明细</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>时段</th><th>订单数</th><th>销售额</th><th>平均客单价</th>
                    </tr>
                </thead>
                <tbody>
"""
    for tp in time_period_analysis:
        html_content += f"""
                    <tr>
                        <td>{tp['time_period']}</td>
                        <td>{tp['order_count']}</td>
                        <td>¥{float(tp['total_amount']):,.2f}</td>
                        <td>¥{float(tp['avg_amount']):,.2f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

# 订单明细
if orders:
    html_content += """
        <div class="section">
            <h2>订单明细</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>开房时间</th><th>包厢号</th><th>开房人</th><th>手机号</th><th>来源渠道</th><th>实收金额</th>
                    </tr>
                </thead>
                <tbody>
"""
    for order in orders:
        open_time = order['open_time'].strftime('%Y-%m-%d %H:%M') if order['open_time'] else ''
        room_no = order['room_no'] or ''
        customer_name = order['customer_name'] or ''
        customer_phone = order['customer_phone'] or ''
        source_channel = order['source_channel'] or ''
        amount = float(order['actual_amount'] or 0)
        html_content += f"""
                    <tr>
                        <td>{open_time}</td>
                        <td>{room_no}</td>
                        <td>{customer_name}</td>
                        <td>{customer_phone}</td>
                        <td>{source_channel}</td>
                        <td>¥{amount:.2f}</td>
                    </tr>
"""
    html_content += """
                </tbody>
            </table>
        </div>
"""

# 添加图表脚本
html_content += """
        <script>
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#ffffff' } }
                },
                scales: {
                    x: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: '#ffffff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            };
"""

# 时段订单数图表
if time_period_analysis:
    labels = [tp['time_period'] for tp in time_period_analysis]
    order_counts = [tp['order_count'] for tp in time_period_analysis]
    amounts = [float(tp['total_amount']) for tp in time_period_analysis]
    
    html_content += """
            new Chart(document.getElementById('periodOrdersChart'), {
                type: 'bar',
                data: {
                    labels: """ + str(labels) + """,
                    datasets: [{
                        label: '订单数',
                        data: """ + str(order_counts) + """,
                        backgroundColor: 'rgba(0,212,255,0.7)',
                        borderColor: '#00d4ff',
                        borderWidth: 2
                    }]
                },
                options: chartOptions
            });

            new Chart(document.getElementById('periodAmountChart'), {
                type: 'bar',
                data: {
                    labels: """ + str(labels) + """,
                    datasets: [{
                        label: '销售额',
                        data: """ + str(amounts) + """,
                        backgroundColor: 'rgba(123,44,191,0.7)',
                        borderColor: '#7b2cbf',
                        borderWidth: 2
                    }]
                },
                options: chartOptions
            });
"""

html_content += """
        </script>
    </div>
</body>
</html>
"""

# 保存文件
output_file = PROJECT_ROOT / "reports" / f"linhejie_daily_{report_date}.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"日报已生成：{output_file}")
print(f"报告日期：{report_date}")
