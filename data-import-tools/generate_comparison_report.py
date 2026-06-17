#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 读取数据
df = pd.read_csv(PROJECT_ROOT / "reports" / "may_stores_data.csv")
df['data_date'] = pd.to_datetime(df['data_date'])

# 分离两个门店的数据
shangdong = df[df['store_name'] == '上东店'].sort_values('data_date')
chenyu = df[df['store_name'] == '晨宇店'].sort_values('data_date')

# 生成报告
html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>上东店 vs 晨宇店 - 5月经营数据对比报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 {
            font-size: 0.95em;
            color: #a0a0a0;
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
            color: #a0a0a0;
            font-size: 0.9em;
        }
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        .section h2 {
            margin-bottom: 25px;
            color: #00d4ff;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }
        .chart-container {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .chart-container h3 {
            margin-bottom: 20px;
            color: #00d4ff;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        .table th, .table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .table th {
            background: rgba(0,0,0,0.2);
            font-weight: 600;
            color: #00d4ff;
        }
        .table tr:hover {
            background: rgba(255,255,255,0.05);
        }
        .positive { color: #4ade80; }
        .negative { color: #ef4444; }
        .shangdong { color: #00d4ff; }
        .chenyu { color: #fb923c; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .summary-item {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .summary-item .label {
            color: #a0a0a0;
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        .summary-item .value {
            font-size: 1.5em;
            font-weight: bold;
        }
        .vs-header {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 20px;
            margin-bottom: 20px;
            align-items: center;
        }
        .vs-store {
            text-align: center;
            padding: 20px;
            border-radius: 12px;
        }
        .vs-store.shangdong {
            background: rgba(0,212,255,0.1);
            border: 1px solid rgba(0,212,255,0.3);
        }
        .vs-store.chenyu {
            background: rgba(251,146,60,0.1);
            border: 1px solid rgba(251,146,60,0.3);
        }
        .vs-store h3 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }
        .vs-divider {
            font-size: 2em;
            font-weight: bold;
            color: #a0a0a0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>上东店 vs 晨宇店</h1>
            <p style="color:#a0a0a0; font-size:1.1em">5月经营数据对比报告</p>
        </header>
"""

# 计算关键指标
sd_total = shangdong['total_revenue'].sum()
cy_total = chenyu['total_revenue'].sum()
sd_avg = shangdong['total_revenue'].mean()
cy_avg = chenyu['total_revenue'].mean()
sd_days = len(shangdong)
cy_days = len(chenyu)
diff_total = sd_total - cy_total
diff_avg = sd_avg - cy_avg

html_content += f"""
        <div class="vs-header">
            <div class="vs-store shangdong">
                <h3 class="shangdong">上东店</h3>
                <div class="summary-item">
                    <div class="label">总营业额</div>
                    <div class="value shangdong">¥{sd_total:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">日均</div>
                    <div class="value shangdong">¥{sd_avg:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">数据天数</div>
                    <div class="value">{sd_days}天</div>
                </div>
            </div>
            <div class="vs-divider">VS</div>
            <div class="vs-store chenyu">
                <h3 class="chenyu">晨宇店</h3>
                <div class="summary-item">
                    <div class="label">总营业额</div>
                    <div class="value chenyu">¥{cy_total:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">日均</div>
                    <div class="value chenyu">¥{cy_avg:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">数据天数</div>
                    <div class="value">{cy_days}天</div>
                </div>
            </div>
        </div>
"""

html_content += f"""
        <div class="dashboard">
            <div class="card">
                <h3>总营业额差额</h3>
                <div class="value {'positive' if diff_total > 0 else 'negative'}">¥{diff_total:,.0f}</div>
                <div class="label">上东店 {'高出' if diff_total > 0 else '低于'}</div>
            </div>
            <div class="card">
                <h3>日均差额</h3>
                <div class="value {'positive' if diff_avg > 0 else 'negative'}">¥{diff_avg:,.0f}</div>
                <div class="label">上东店 {'高出' if diff_avg > 0 else '低于'}</div>
            </div>
            <div class="card">
                <h3>日均百分比</h3>
                <div class="value {'positive' if (sd_avg/cy_avg-1) > 0 else 'negative'}">{(sd_avg/cy_avg-1)*100:.1f}%</div>
                <div class="label">上东店 {'高于' if (sd_avg/cy_avg-1) > 0 else '低于'}晨宇店</div>
            </div>
        </div>
"""

# 收入构成对比
sd_supermarket = shangdong['supermarket_revenue'].sum()
sd_room = shangdong['room_revenue'].sum()
sd_stored = shangdong['stored_card_sales'].sum()
cy_supermarket = chenyu['supermarket_revenue'].sum()
cy_room = chenyu['room_revenue'].sum()
cy_stored = chenyu['stored_card_sales'].sum()

html_content += f"""
        <div class="section">
            <h2>收入构成对比</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>收入结构</h3>
                    <canvas id="revenueBreakdown"></canvas>
                </div>
                <div class="chart-container">
                    <h3>日营业额趋势</h3>
                    <canvas id="dailyTrend"></canvas>
                </div>
            </div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">上东店 - 超市收入</div>
                    <div class="value shangdong">¥{sd_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">晨宇店 - 超市收入</div>
                    <div class="value chenyu">¥{cy_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">上东店 - 房费收入</div>
                    <div class="value shangdong">¥{sd_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">晨宇店 - 房费收入</div>
                    <div class="value chenyu">¥{cy_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">上东店 - 储值卡销售</div>
                    <div class="value shangdong">¥{sd_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">晨宇店 - 储值卡销售</div>
                    <div class="value chenyu">¥{cy_stored:,.0f}</div>
                </div>
            </div>
        </div>
"""

# 待客台数对比
sd_customers = shangdong['customers'].sum()
cy_customers = chenyu['customers'].sum()
sd_avg_customers = shangdong['customers'].mean()
cy_avg_customers = chenyu['customers'].mean()

html_content += f"""
        <div class="section">
            <h2>待客台数对比</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>总待客台数</h3>
                    <canvas id="customersTotal"></canvas>
                </div>
                <div class="chart-container">
                    <h3>日均待客台数</h3>
                    <canvas id="customersAvg"></canvas>
                </div>
            </div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">上东店 - 总待客台数</div>
                    <div class="value shangdong">{sd_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">晨宇店 - 总待客台数</div>
                    <div class="value chenyu">{cy_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">上东店 - 日均待客</div>
                    <div class="value shangdong">{sd_avg_customers:.1f}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">晨宇店 - 日均待客</div>
                    <div class="value chenyu">{cy_avg_customers:.1f}台</div>
                </div>
            </div>
        </div>
"""

# 详细数据表格
html_content += f"""
        <div class="section">
            <h2>每日经营明细</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>星期</th>
                        <th class="shangdong">上东店</th>
                        <th class="chenyu">晨宇店</th>
                        <th>差额</th>
                    </tr>
                </thead>
                <tbody>
"""

# 合并数据并生成表格
# 创建日期索引
shangdong_dict = {}
for _, row in shangdong.iterrows():
    date_key = str(row['data_date'])[:10]
    shangdong_dict[date_key] = {
        'weekday': row['weekday'],
        'total_revenue': row['total_revenue']
    }

chenyu_dict = {}
for _, row in chenyu.iterrows():
    date_key = str(row['data_date'])[:10]
    chenyu_dict[date_key] = {
        'weekday': row['weekday'],
        'total_revenue': row['total_revenue']
    }

all_dates = sorted(list(set(shangdong_dict.keys()) | set(chenyu_dict.keys())))

for date_str in all_dates:
    sd_row = shangdong_dict.get(date_str)
    cy_row = chenyu_dict.get(date_str)
    
    if sd_row:
        weekday = sd_row['weekday']
        sd_rev = sd_row['total_revenue']
    else:
        weekday = cy_row['weekday'] if cy_row else ''
        sd_rev = None
    
    cy_rev = cy_row['total_revenue'] if cy_row else None
    diff = (sd_rev - cy_rev) if (sd_rev is not None and cy_rev is not None) else None
    
    sd_str = f"¥{sd_rev:,.2f}" if sd_rev is not None else '-'
    cy_str = f"¥{cy_rev:,.2f}" if cy_rev is not None else '-'
    diff_str = f"¥{diff:,.2f}" if diff is not None else '-'
    diff_class = 'positive' if (diff is not None and diff > 0) else 'negative' if (diff is not None and diff < 0) else ''
    
    html_content += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{weekday}</td>
                        <td class="shangdong">{sd_str}</td>
                        <td class="chenyu">{cy_str}</td>
                        <td class="{diff_class}">{diff_str}</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>
"""

# 图表数据
# 准备日趋势数据
sd_dates = [str(d)[:10] for d in shangdong['data_date']]
sd_values = shangdong['total_revenue'].tolist()
cy_dates = [str(d)[:10] for d in chenyu['data_date']]
cy_values = chenyu['total_revenue'].tolist()

# 对齐日期
all_dates_sorted = sorted(list(set(sd_dates + cy_dates)))
sd_values_aligned = []
cy_values_aligned = []

for d in all_dates_sorted:
    if d in shangdong_dict:
        sd_values_aligned.append(shangdong_dict[d]['total_revenue'])
    else:
        sd_values_aligned.append(0)
    if d in chenyu_dict:
        cy_values_aligned.append(chenyu_dict[d]['total_revenue'])
    else:
        cy_values_aligned.append(0)

html_content += f"""
        <script>
            const chartOptions = {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ labels: {{ color: '#ffffff' }} }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#ffffff' }}, grid: {{ color: 'rgba(255,255,255,0.1)' }} }},
                    y: {{ ticks: {{ color: '#ffffff' }}, grid: {{ color: 'rgba(255,255,255,0.1)' }} }}
                }}
            }};

            // 收入结构图表
            new Chart(document.getElementById('revenueBreakdown'), {{
                type: 'bar',
                data: {{
                    labels: ['超市收入', '房费收入', '储值卡销售'],
                    datasets: [
                        {{
                            label: '上东店',
                            data: [{sd_supermarket}, {sd_room}, {sd_stored}],
                            backgroundColor: 'rgba(0,212,255,0.7)',
                            borderColor: '#00d4ff',
                            borderWidth: 2
                        }},
                        {{
                            label: '晨宇店',
                            data: [{cy_supermarket}, {cy_room}, {cy_stored}],
                            backgroundColor: 'rgba(251,146,60,0.7)',
                            borderColor: '#fb923c',
                            borderWidth: 2
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 日趋势图表
            new Chart(document.getElementById('dailyTrend'), {{
                type: 'line',
                data: {{
                    labels: {all_dates_sorted},
                    datasets: [
                        {{
                            label: '上东店',
                            data: {sd_values_aligned},
                            borderColor: '#00d4ff',
                            backgroundColor: 'rgba(0,212,255,0.2)',
                            tension: 0.3,
                            fill: true
                        }},
                        {{
                            label: '晨宇店',
                            data: {cy_values_aligned},
                            borderColor: '#fb923c',
                            backgroundColor: 'rgba(251,146,60,0.2)',
                            tension: 0.3,
                            fill: true
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 总待客台数
            new Chart(document.getElementById('customersTotal'), {{
                type: 'bar',
                data: {{
                    labels: ['总待客台数'],
                    datasets: [
                        {{
                            label: '上东店',
                            data: [{sd_customers}],
                            backgroundColor: 'rgba(0,212,255,0.7)',
                            borderColor: '#00d4ff',
                            borderWidth: 2
                        }},
                        {{
                            label: '晨宇店',
                            data: [{cy_customers}],
                            backgroundColor: 'rgba(251,146,60,0.7)',
                            borderColor: '#fb923c',
                            borderWidth: 2
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 日均待客台数
            new Chart(document.getElementById('customersAvg'), {{
                type: 'bar',
                data: {{
                    labels: ['日均待客台数'],
                    datasets: [
                        {{
                            label: '上东店',
                            data: [{sd_avg_customers}],
                            backgroundColor: 'rgba(0,212,255,0.7)',
                            borderColor: '#00d4ff',
                            borderWidth: 2
                        }},
                        {{
                            label: '晨宇店',
                            data: [{cy_avg_customers}],
                            backgroundColor: 'rgba(251,146,60,0.7)',
                            borderColor: '#fb923c',
                            borderWidth: 2
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
output_file = PROJECT_ROOT / "reports" / "shangdong_vs_chenyu_may_comparison.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"\n✅ 对比报告已生成: {output_file}")
print(f"\n📊 报告要点:")
print(f"   • 上东店总营业额: ¥{sd_total:,.0f} (日均 ¥{sd_avg:,.0f})")
print(f"   • 晨宇店总营业额: ¥{cy_total:,.0f} (日均 ¥{cy_avg:,.0f})")
print(f"   • 上东店高出晨宇店: ¥{diff_total:,.0f} ({(diff_total/cy_total*100):.1f}%)")
