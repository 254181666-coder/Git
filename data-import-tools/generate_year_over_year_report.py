#!/usr/bin/env python3
import sys
from pathlib import Path
import pymysql
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("📊 生成去年5月 vs 今年5月同期对比报告...\n")

def get_store_data(store_name, year, month):
    cursor.execute("""
        SELECT 
            data_date,
            weekday,
            total_revenue,
            actual_amount,
            supermarket_revenue,
            room_revenue,
            stored_card_sales,
            customers
        FROM store_daily
        WHERE store_id = (SELECT id FROM stores WHERE store_name = %s)
            AND YEAR(data_date) = %s
            AND MONTH(data_date) = %s
        ORDER BY data_date
    """, (store_name, year, month))
    return cursor.fetchall()

# 获取数据
shangdong_2025 = get_store_data('上东店', 2025, 5)
shangdong_2026 = get_store_data('上东店', 2026, 5)
chenyu_2025 = get_store_data('晨宇店', 2025, 5)
chenyu_2026 = get_store_data('晨宇店', 2026, 5)

# 对齐日期 - 只比较两个年份都有的日期，且不超过5月13日
def align_data(data_2025, data_2026):
    data_2025_dict = {str(d['data_date'])[5:]: d for d in data_2025}
    data_2026_dict = {str(d['data_date'])[5:]: d for d in data_2026}
    
    common_dates = sorted(list(set(data_2025_dict.keys()) & set(data_2026_dict.keys())))
    
    # 只保留到5月13日的日期
    filtered_dates = [d for d in common_dates if (len(d) > 3 and int(d[3:]) <= 13) or d == "05-13"]
    
    aligned_2025 = [data_2025_dict[d] for d in filtered_dates]
    aligned_2026 = [data_2026_dict[d] for d in filtered_dates]
    
    # 提取日期中的日部分，用于显示
    display_dates = [d[3:] if len(d) > 3 else d for d in filtered_dates]
    
    return aligned_2025, aligned_2026, filtered_dates, display_dates

sd_2025_aligned, sd_2026_aligned, sd_common_dates, sd_display_dates = align_data(shangdong_2025, shangdong_2026)
cy_2025_aligned, cy_2026_aligned, cy_common_dates, cy_display_dates = align_data(chenyu_2025, chenyu_2026)

cursor.close()
conn.close()

# 计算对齐后的数据
def calc_metrics(data):
    if not data:
        return 0, 0, 0, 0, 0, 0
    total = sum(d['total_revenue'] for d in data)
    avg = total / len(data)
    supermarket = sum(d['supermarket_revenue'] for d in data)
    room = sum(d['room_revenue'] for d in data)
    stored = sum(d['stored_card_sales'] for d in data)
    customers = sum(d['customers'] for d in data)
    return len(data), total, avg, supermarket, room, stored, customers

sd_2025_days, sd_2025_total, sd_2025_avg, sd_2025_supermarket, sd_2025_room, sd_2025_stored, sd_2025_customers = calc_metrics(sd_2025_aligned)
sd_2026_days, sd_2026_total, sd_2026_avg, sd_2026_supermarket, sd_2026_room, sd_2026_stored, sd_2026_customers = calc_metrics(sd_2026_aligned)

cy_2025_days, cy_2025_total, cy_2025_avg, cy_2025_supermarket, cy_2025_room, cy_2025_stored, cy_2025_customers = calc_metrics(cy_2025_aligned)
cy_2026_days, cy_2026_total, cy_2026_avg, cy_2026_supermarket, cy_2026_room, cy_2026_stored, cy_2026_customers = calc_metrics(cy_2026_aligned)

sd_total_diff = sd_2026_total - sd_2025_total
sd_avg_diff = sd_2026_avg - sd_2025_avg
sd_total_pct = (sd_total_diff / sd_2025_total * 100) if sd_2025_total > 0 else 0

cy_total_diff = cy_2026_total - cy_2025_total
cy_avg_diff = cy_2026_avg - cy_2025_avg
cy_total_pct = (cy_total_diff / cy_2025_total * 100) if cy_2025_total > 0 else 0

# 生成报告 - 白色干净的样式
html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>去年5月 vs 今年5月 - 同期对比报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #ffffff;
            color: #333333;
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
            border-bottom: 2px solid #e0e0e0;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #333333;
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
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }
        .card h3 {
            font-size: 0.9em;
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
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            border: 1px solid #e0e0e0;
            margin-bottom: 30px;
        }
        .section h2 {
            margin-bottom: 25px;
            color: #333333;
            font-size: 1.5em;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        .chart-container {
            background: #ffffff;
            border-radius: 12px;
            padding: 30px;
            border: 1px solid #e0e0e0;
        }
        .chart-container h4 {
            margin-bottom: 20px;
            color: #333333;
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
            background: #f0f0f0;
            font-weight: 600;
            color: #333333;
        }
        .table tr:hover {
            background: #f8f9fa;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .summary-item {
            background: #ffffff;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #e0e0e0;
        }
        .summary-item .label {
            color: #666666;
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        .summary-item .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333333;
        }
        .store-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        .store-name {
            font-size: 1.8em;
            font-weight: bold;
            color: #333333;
        }
        .store-period {
            font-size: 1em;
            color: #666666;
        }
        .date-label {
            color: #666666;
            font-size: 0.9em;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>去年5月 vs 今年5月 - 同期对比报告</h1>
            <p class="subtitle">上东店 & 晨宇店</p>
        </header>
"""

html_content += f"""
        <div class="dashboard">
            <div class="card">
                <h3>上东店 - 总营业额变化</h3>
                <div class="value {'positive' if sd_total_diff > 0 else 'negative'}">
                    ¥{sd_total_diff:,.0f}
                </div>
                <div class="label">
                    {'+ ' if sd_total_pct > 0 else ''}{sd_total_pct:.1f}%
                </div>
            </div>
            <div class="card">
                <h3>晨宇店 - 总营业额变化</h3>
                <div class="value {'positive' if cy_total_diff > 0 else 'negative'}">
                    ¥{cy_total_diff:,.0f}
                </div>
                <div class="label">
                    {'+ ' if cy_total_pct > 0 else ''}{cy_total_pct:.1f}%
                </div>
            </div>
            <div class="card">
                <h3>上东店 - 日均变化</h3>
                <div class="value {'positive' if sd_avg_diff > 0 else 'negative'}">
                    ¥{sd_avg_diff:,.0f}
                </div>
                <div class="label">
                    今年 ¥{sd_2026_avg:,.0f} vs 去年 ¥{sd_2025_avg:,.0f}
                </div>
            </div>
            <div class="card">
                <h3>晨宇店 - 日均变化</h3>
                <div class="value {'positive' if cy_avg_diff > 0 else 'negative'}">
                    ¥{cy_avg_diff:,.0f}
                </div>
                <div class="label">
                    今年 ¥{cy_2026_avg:,.0f} vs 去年 ¥{cy_2025_avg:,.0f}
                </div>
            </div>
        </div>
"""

# 上东店详情
html_content += f"""
        <div class="section">
            <div class="store-header">
                <div class="store-name">上东店</div>
                <div class="store-period">2025年5月 vs 2026年5月</div>
            </div>
            <p class="date-label">对比日期: 5月{sd_display_dates[0]}日 - 5月{sd_display_dates[-1]}日 ({sd_2025_days}天)</p>
            
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">去年总营业额</div>
                    <div class="value">¥{sd_2025_total:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年总营业额</div>
                    <div class="value">¥{sd_2026_total:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年超市收入</div>
                    <div class="value">¥{sd_2025_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年超市收入</div>
                    <div class="value">¥{sd_2026_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年房费收入</div>
                    <div class="value">¥{sd_2025_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年房费收入</div>
                    <div class="value">¥{sd_2026_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年储值卡销售</div>
                    <div class="value">¥{sd_2025_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年储值卡销售</div>
                    <div class="value">¥{sd_2026_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年总待客台数</div>
                    <div class="value">{sd_2025_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年总待客台数</div>
                    <div class="value">{sd_2026_customers:,}台</div>
                </div>
            </div>
        </div>
"""

# 晨宇店详情
html_content += f"""
        <div class="section">
            <div class="store-header">
                <div class="store-name">晨宇店</div>
                <div class="store-period">2025年5月 vs 2026年5月</div>
            </div>
            <p class="date-label">对比日期: 5月{cy_display_dates[0]}日 - 5月{cy_display_dates[-1]}日 ({cy_2025_days}天)</p>
            
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">去年总营业额</div>
                    <div class="value">¥{cy_2025_total:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年总营业额</div>
                    <div class="value">¥{cy_2026_total:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年超市收入</div>
                    <div class="value">¥{cy_2025_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年超市收入</div>
                    <div class="value">¥{cy_2026_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年房费收入</div>
                    <div class="value">¥{cy_2025_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年房费收入</div>
                    <div class="value">¥{cy_2026_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年储值卡销售</div>
                    <div class="value">¥{cy_2025_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年储值卡销售</div>
                    <div class="value">¥{cy_2026_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">去年总待客台数</div>
                    <div class="value">{cy_2025_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">今年总待客台数</div>
                    <div class="value">{cy_2026_customers:,}台</div>
                </div>
            </div>
        </div>
"""

# 准备每日对比数据
sd_2025_values = [d['total_revenue'] for d in sd_2025_aligned]
sd_2026_values = [d['total_revenue'] for d in sd_2026_aligned]
cy_2025_values = [d['total_revenue'] for d in cy_2025_aligned]
cy_2026_values = [d['total_revenue'] for d in cy_2026_aligned]
sd_chart_dates = sd_display_dates
cy_chart_dates = cy_display_dates

# 图表
html_content += f"""
        <div class="section">
            <h2>可视化对比</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h4>上东店 - 总营业额对比</h4>
                    <canvas id="sdTotalChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>晨宇店 - 总营业额对比</h4>
                    <canvas id="cyTotalChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>收入构成对比 - 上东店</h4>
                    <canvas id="sdBreakdownChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>收入构成对比 - 晨宇店</h4>
                    <canvas id="cyBreakdownChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>上东店 - 每日对比</h4>
                    <canvas id="sdDailyChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>晨宇店 - 每日对比</h4>
                    <canvas id="cyDailyChart"></canvas>
                </div>
            </div>
        </div>
"""

html_content += f"""
        <script>
            const chartOptions = {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ labels: {{ color: '#333333' }} }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#666666' }}, grid: {{ color: '#e0e0e0' }} }},
                    y: {{ ticks: {{ color: '#666666' }}, grid: {{ color: '#e0e0e0' }} }}
                }}
            }};

            // 上东店总营业额
            new Chart(document.getElementById('sdTotalChart'), {{
                type: 'bar',
                data: {{
                    labels: ['2025年5月', '2026年5月'],
                    datasets: [{{
                        label: '总营业额',
                        data: [{sd_2025_total}, {sd_2026_total}],
                        backgroundColor: ['#3b82f6', '#10b981'],
                        borderWidth: 0
                    }}]
                }},
                options: chartOptions
            }});

            // 晨宇店总营业额
            new Chart(document.getElementById('cyTotalChart'), {{
                type: 'bar',
                data: {{
                    labels: ['2025年5月', '2026年5月'],
                    datasets: [{{
                        label: '总营业额',
                        data: [{cy_2025_total}, {cy_2026_total}],
                        backgroundColor: ['#f59e0b', '#8b5cf6'],
                        borderWidth: 0
                    }}]
                }},
                options: chartOptions
            }});

            // 上东店收入构成
            new Chart(document.getElementById('sdBreakdownChart'), {{
                type: 'bar',
                data: {{
                    labels: ['超市收入', '房费收入', '储值卡销售'],
                    datasets: [
                        {{
                            label: '2025年5月',
                            data: [{sd_2025_supermarket}, {sd_2025_room}, {sd_2025_stored}],
                            backgroundColor: '#3b82f6'
                        }},
                        {{
                            label: '2026年5月',
                            data: [{sd_2026_supermarket}, {sd_2026_room}, {sd_2026_stored}],
                            backgroundColor: '#10b981'
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 晨宇店收入构成
            new Chart(document.getElementById('cyBreakdownChart'), {{
                type: 'bar',
                data: {{
                    labels: ['超市收入', '房费收入', '储值卡销售'],
                    datasets: [
                        {{
                            label: '2025年5月',
                            data: [{cy_2025_supermarket}, {cy_2025_room}, {cy_2025_stored}],
                            backgroundColor: '#f59e0b'
                        }},
                        {{
                            label: '2026年5月',
                            data: [{cy_2026_supermarket}, {cy_2026_room}, {cy_2026_stored}],
                            backgroundColor: '#8b5cf6'
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 上东店每日对比
            new Chart(document.getElementById('sdDailyChart'), {{
                type: 'line',
                data: {{
                    labels: {sd_chart_dates},
                    datasets: [
                        {{
                            label: '2025年',
                            data: {sd_2025_values},
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            tension: 0.3,
                            fill: true
                        }},
                        {{
                            label: '2026年',
                            data: {sd_2026_values},
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.3,
                            fill: true
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 晨宇店每日对比
            new Chart(document.getElementById('cyDailyChart'), {{
                type: 'line',
                data: {{
                    labels: {cy_chart_dates},
                    datasets: [
                        {{
                            label: '2025年',
                            data: {cy_2025_values},
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            tension: 0.3,
                            fill: true
                        }},
                        {{
                            label: '2026年',
                            data: {cy_2026_values},
                            borderColor: '#8b5cf6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            tension: 0.3,
                            fill: true
                        }}
                    ]
                }},
                options: chartOptions
            }});
        </script>
    </div>
</body>
</html>
"""

# 保存文件
output_file = PROJECT_ROOT / "reports" / "year_over_year_may_comparison.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"✅ 同期对比报告已生成: {output_file}")
print(f"\n📊 报告要点:")
print(f"   上东店:")
print(f"     对比日期: 5月{sd_display_dates[0]}日 - 5月{sd_display_dates[-1]}日 ({sd_2025_days}天)")
print(f"     2025年5月: ¥{sd_2025_total:,.0f}")
print(f"     2026年5月: ¥{sd_2026_total:,.0f}")
print(f"     变化: {'+' if sd_total_pct > 0 else ''}{sd_total_pct:.1f}%")
print(f"\n   晨宇店:")
print(f"     对比日期: 5月{cy_display_dates[0]}日 - 5月{cy_display_dates[-1]}日 ({cy_2025_days}天)")
print(f"     2025年5月: ¥{cy_2025_total:,.0f}")
print(f"     2026年5月: ¥{cy_2026_total:,.0f}")
print(f"     变化: {'+' if cy_total_pct > 0 else ''}{cy_total_pct:.1f}%")
