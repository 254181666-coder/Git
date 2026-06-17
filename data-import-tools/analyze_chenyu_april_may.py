#!/usr/bin/env python3
import sys
from pathlib import Path
import pymysql
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)

# 查询晨宇店2025年、2026年4-5月数据
query = """
SELECT 
    data_date, weekday, total_revenue, actual_amount,
    supermarket_revenue, room_revenue, stored_card_sales, times_card_sales,
    customers, customers_before_18, customers_18_to_24, customers_after_00
FROM store_daily 
WHERE store_id = (SELECT id FROM stores WHERE store_name = '晨宇店')
AND (
    (data_date BETWEEN '2025-04-01' AND '2025-05-31')
    OR
    (data_date BETWEEN '2026-04-01' AND '2026-05-15')
)
ORDER BY data_date
"""

df = pd.read_sql(query, conn)
df['data_date'] = pd.to_datetime(df['data_date'])
df['year'] = df['data_date'].dt.year
df['month'] = df['data_date'].dt.month
df['day'] = df['data_date'].dt.day

conn.close()

# 分离不同时间段数据，5月只取前15天以对齐日期
data_2025_april = df[(df['year'] == 2025) & (df['month'] == 4)]
data_2025_may = df[(df['year'] == 2025) & (df['month'] == 5) & (df['day'] <= 15)]
data_2026_april = df[(df['year'] == 2026) & (df['month'] == 4)]
data_2026_may = df[(df['year'] == 2026) & (df['month'] == 5) & (df['day'] <= 15)]

print("数据统计：")
print(f"  2025年4月：{len(data_2025_april)}天")
print(f"  2025年5月：{len(data_2025_may)}天")
print(f"  2026年4月：{len(data_2026_april)}天")
print(f"  2026年5月：{len(data_2026_may)}天")

# 计算各时段待客台次汇总
def calculate_period_stats(data):
    if len(data) == 0:
        return {
            'before_18': 0, 'eight_to_twenty_four': 0, 'after_zero': 0, 'total': 0, 'days': 0
        }
    return {
        'before_18': data['customers_before_18'].sum(),
        'eight_to_twenty_four': data['customers_18_to_24'].sum(),
        'after_zero': data['customers_after_00'].sum(),
        'total': data['customers'].sum(),
        'days': len(data)
    }

# 获取各时段数据
stats_2025_april = calculate_period_stats(data_2025_april)
stats_2025_may = calculate_period_stats(data_2025_may)
stats_2026_april = calculate_period_stats(data_2026_april)
stats_2026_may = calculate_period_stats(data_2026_may)

# 计算同比和环比
def calculate_growth(current, base):
    if base == 0:
        return 0, 0
    absolute = current - base
    percentage = (absolute / base) * 100
    return absolute, percentage

# 2026年4月的同比
april_yoy_before_18, april_yoy_before_18_pct = calculate_growth(stats_2026_april['before_18'], stats_2025_april['before_18'])
april_yoy_eight_to_twenty_four, april_yoy_eight_to_twenty_four_pct = calculate_growth(stats_2026_april['eight_to_twenty_four'], stats_2025_april['eight_to_twenty_four'])
april_yoy_after_zero, april_yoy_after_zero_pct = calculate_growth(stats_2026_april['after_zero'], stats_2025_april['after_zero'])
april_yoy_total, april_yoy_total_pct = calculate_growth(stats_2026_april['total'], stats_2025_april['total'])

# 2026年5月的同比和环比
may_yoy_before_18, may_yoy_before_18_pct = calculate_growth(stats_2026_may['before_18'], stats_2025_may['before_18'])
may_yoy_eight_to_twenty_four, may_yoy_eight_to_twenty_four_pct = calculate_growth(stats_2026_may['eight_to_twenty_four'], stats_2025_may['eight_to_twenty_four'])
may_yoy_after_zero, may_yoy_after_zero_pct = calculate_growth(stats_2026_may['after_zero'], stats_2025_may['after_zero'])
may_yoy_total, may_yoy_total_pct = calculate_growth(stats_2026_may['total'], stats_2025_may['total'])

may_mom_before_18, may_mom_before_18_pct = calculate_growth(stats_2026_may['before_18'], stats_2026_april['before_18'])
may_mom_eight_to_twenty_four, may_mom_eight_to_twenty_four_pct = calculate_growth(stats_2026_may['eight_to_twenty_four'], stats_2026_april['eight_to_twenty_four'])
may_mom_after_zero, may_mom_after_zero_pct = calculate_growth(stats_2026_may['after_zero'], stats_2026_april['after_zero'])
may_mom_total, may_mom_total_pct = calculate_growth(stats_2026_may['total'], stats_2026_april['total'])

# 生成HTML报告
html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>晨宇店 - 4月vs5月经营数据对比报告</title>
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
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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
        .card .sub-value {
            font-size: 0.9em;
            margin-top: 5px;
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
        .positive { color: #16a34a; }
        .negative { color: #dc2626; }
        .april { color: #0066cc; }
        .may { color: #ea580c; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .summary-item {
            background: #f8f9fa;
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
        .vs-store.april {
            background: #e6f0ff;
            border: 1px solid #b3d1ff;
        }
        .vs-store.may {
            background: #fff3e6;
            border: 1px solid #ffd6b3;
        }
        .vs-store h3 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }
        .vs-divider {
            font-size: 2em;
            font-weight: bold;
            color: #666666;
        }
        .insights {
            background: #f0e6ff;
            border: 1px solid #d9b3ff;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        .insights h3 {
            color: #7c3aed;
            margin-bottom: 15px;
        }
        .insights ul {
            list-style: none;
            padding: 0;
        }
        .insights li {
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        .insights li:last-child {
            border-bottom: none;
        }
        .insights li::before {
            content: "💡";
            margin-right: 10px;
        }
        .period-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.9em;
        }
        .period-table th, .period-table td {
            padding: 12px 15px;
            text-align: center;
            border: 1px solid #e0e0e0;
        }
        .period-table th {
            background: #f0f7ff;
            font-weight: 600;
            color: #0066cc;
        }
        .period-table .section-header {
            background: #e9ecef;
            font-weight: bold;
            text-align: left;
        }
        .period-table .growth-positive {
            color: #16a34a;
            font-weight: 500;
        }
        .period-table .growth-negative {
            color: #dc2626;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>晨宇店经营数据分析</h1>
            <p style="color:#666666; font-size:1.1em">4月 vs 5月对比报告（含同比环比）</p>
        </header>
"""

# 计算关键指标
april_total = data_2026_april['total_revenue'].sum()
may_total = data_2026_may['total_revenue'].sum()
april_avg = data_2026_april['total_revenue'].mean()
may_avg = data_2026_may['total_revenue'].mean()
april_days = len(data_2026_april)
may_days = len(data_2026_may)
diff_total = may_total - april_total
diff_avg = may_avg - april_avg
growth_rate = (diff_total / april_total * 100) if april_total > 0 else 0

html_content += f"""
        <div class="vs-header">
            <div class="vs-store april">
                <h3 class="april">2026年4月</h3>
                <div class="summary-item">
                    <div class="label">总营业额</div>
                    <div class="value april">¥{april_total:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">日均</div>
                    <div class="value april">¥{april_avg:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">数据天数</div>
                    <div class="value">{april_days}天</div>
                </div>
            </div>
            <div class="vs-divider">VS</div>
            <div class="vs-store may">
                <h3 class="may">2026年5月</h3>
                <div class="summary-item">
                    <div class="label">总营业额</div>
                    <div class="value may">¥{may_total:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">日均</div>
                    <div class="value may">¥{may_avg:,.0f}</div>
                </div>
                <div class="summary-item" style="margin-top:15px">
                    <div class="label">数据天数</div>
                    <div class="value">{may_days}天</div>
                </div>
            </div>
        </div>
"""

html_content += f"""
        <div class="dashboard">
            <div class="card">
                <h3>总营业额变化</h3>
                <div class="value {'positive' if diff_total > 0 else 'negative'}">¥{diff_total:,.0f}</div>
                <div class="label">5月 {'增长' if diff_total > 0 else '下降'}</div>
            </div>
            <div class="card">
                <h3>日均变化</h3>
                <div class="value {'positive' if diff_avg > 0 else 'negative'}">¥{diff_avg:,.0f}</div>
                <div class="label">5月 {'增长' if diff_avg > 0 else '下降'}</div>
            </div>
            <div class="card">
                <h3>增长率</h3>
                <div class="value {'positive' if growth_rate > 0 else 'negative'}">{growth_rate:+.1f}%</div>
                <div class="label">5月较4月</div>
            </div>
        </div>
"""

# 收入构成对比
april_supermarket = data_2026_april['supermarket_revenue'].sum()
april_room = data_2026_april['room_revenue'].sum()
april_stored = data_2026_april['stored_card_sales'].sum()
april_times = data_2026_april['times_card_sales'].sum()
may_supermarket = data_2026_may['supermarket_revenue'].sum()
may_room = data_2026_may['room_revenue'].sum()
may_stored = data_2026_may['stored_card_sales'].sum()
may_times = data_2026_may['times_card_sales'].sum()

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
                    <div class="label">4月 - 超市收入</div>
                    <div class="value april">¥{april_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 超市收入</div>
                    <div class="value may">¥{may_supermarket:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">4月 - 房费收入</div>
                    <div class="value april">¥{april_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 房费收入</div>
                    <div class="value may">¥{may_room:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">4月 - 储值卡销售</div>
                    <div class="value april">¥{april_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 储值卡销售</div>
                    <div class="value may">¥{may_stored:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">4月 - 次卡销售</div>
                    <div class="value april">¥{april_times:,.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 次卡销售</div>
                    <div class="value may">¥{may_times:,.0f}</div>
                </div>
            </div>
        </div>
"""

# 待客台数对比
april_customers = data_2026_april['customers'].sum()
may_customers = data_2026_may['customers'].sum()
april_avg_customers = data_2026_april['customers'].mean()
may_avg_customers = data_2026_may['customers'].mean()

# 时段分析
april_before_18 = data_2026_april['customers_before_18'].sum()
april_eight_to_twenty_four = data_2026_april['customers_18_to_24'].sum()
april_after_zero = data_2026_april['customers_after_00'].sum()
may_before_18 = data_2026_may['customers_before_18'].sum()
may_eight_to_twenty_four = data_2026_may['customers_18_to_24'].sum()
may_after_zero = data_2026_may['customers_after_00'].sum()

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
                <div class="chart-container">
                    <h3>时段待客分布</h3>
                    <canvas id="timePeriod"></canvas>
                </div>
            </div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">4月 - 总待客台数</div>
                    <div class="value april">{april_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 总待客台数</div>
                    <div class="value may">{may_customers:,}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">4月 - 日均待客</div>
                    <div class="value april">{april_avg_customers:.1f}台</div>
                </div>
                <div class="summary-item">
                    <div class="label">5月 - 日均待客</div>
                    <div class="value may">{may_avg_customers:.1f}台</div>
                </div>
            </div>
        </div>
"""

# 时段同比环比分析表格
html_content += f"""
        <div class="section">
            <h2>各时段待客台次同比环比分析</h2>
            <table class="period-table">
                <thead>
                    <tr>
                        <th>时段</th>
                        <th>2025年4月</th>
                        <th>2025年5月1-15日</th>
                        <th>2026年4月</th>
                        <th>2026年5月1-15日</th>
                        <th>4月同比</th>
                        <th>5月同比</th>
                        <th>5月环比</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td colspan="8" class="section-header">18点前</td>
                    </tr>
                    <tr>
                        <td>待客台次</td>
                        <td>{stats_2025_april['before_18']:,}</td>
                        <td>{stats_2025_may['before_18']:,}</td>
                        <td>{stats_2026_april['before_18']:,}</td>
                        <td>{stats_2026_may['before_18']:,}</td>
                        <td class="{'growth-positive' if april_yoy_before_18 >= 0 else 'growth-negative'}">
                            {f'+{april_yoy_before_18:,.0f}' if april_yoy_before_18 >= 0 else f'{april_yoy_before_18:,.0f}'} ({april_yoy_before_18_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_yoy_before_18 >= 0 else 'growth-negative'}">
                            {f'+{may_yoy_before_18:,.0f}' if may_yoy_before_18 >= 0 else f'{may_yoy_before_18:,.0f}'} ({may_yoy_before_18_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_mom_before_18 >= 0 else 'growth-negative'}">
                            {f'+{may_mom_before_18:,.0f}' if may_mom_before_18 >= 0 else f'{may_mom_before_18:,.0f}'} ({may_mom_before_18_pct:+.1f}%)
                        </td>
                    </tr>
                    <tr>
                        <td colspan="8" class="section-header">18-24点</td>
                    </tr>
                    <tr>
                        <td>待客台次</td>
                        <td>{stats_2025_april['eight_to_twenty_four']:,}</td>
                        <td>{stats_2025_may['eight_to_twenty_four']:,}</td>
                        <td>{stats_2026_april['eight_to_twenty_four']:,}</td>
                        <td>{stats_2026_may['eight_to_twenty_four']:,}</td>
                        <td class="{'growth-positive' if april_yoy_eight_to_twenty_four >= 0 else 'growth-negative'}">
                            {f'+{april_yoy_eight_to_twenty_four:,.0f}' if april_yoy_eight_to_twenty_four >= 0 else f'{april_yoy_eight_to_twenty_four:,.0f}'} ({april_yoy_eight_to_twenty_four_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_yoy_eight_to_twenty_four >= 0 else 'growth-negative'}">
                            {f'+{may_yoy_eight_to_twenty_four:,.0f}' if may_yoy_eight_to_twenty_four >= 0 else f'{may_yoy_eight_to_twenty_four:,.0f}'} ({may_yoy_eight_to_twenty_four_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_mom_eight_to_twenty_four >= 0 else 'growth-negative'}">
                            {f'+{may_mom_eight_to_twenty_four:,.0f}' if may_mom_eight_to_twenty_four >= 0 else f'{may_mom_eight_to_twenty_four:,.0f}'} ({may_mom_eight_to_twenty_four_pct:+.1f}%)
                        </td>
                    </tr>
                    <tr>
                        <td colspan="8" class="section-header">00点后</td>
                    </tr>
                    <tr>
                        <td>待客台次</td>
                        <td>{stats_2025_april['after_zero']:,}</td>
                        <td>{stats_2025_may['after_zero']:,}</td>
                        <td>{stats_2026_april['after_zero']:,}</td>
                        <td>{stats_2026_may['after_zero']:,}</td>
                        <td class="{'growth-positive' if april_yoy_after_zero >= 0 else 'growth-negative'}">
                            {f'+{april_yoy_after_zero:,.0f}' if april_yoy_after_zero >= 0 else f'{april_yoy_after_zero:,.0f}'} ({april_yoy_after_zero_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_yoy_after_zero >= 0 else 'growth-negative'}">
                            {f'+{may_yoy_after_zero:,.0f}' if may_yoy_after_zero >= 0 else f'{may_yoy_after_zero:,.0f}'} ({may_yoy_after_zero_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_mom_after_zero >= 0 else 'growth-negative'}">
                            {f'+{may_mom_after_zero:,.0f}' if may_mom_after_zero >= 0 else f'{may_mom_after_zero:,.0f}'} ({may_mom_after_zero_pct:+.1f}%)
                        </td>
                    </tr>
                    <tr>
                        <td colspan="8" class="section-header">合计</td>
                    </tr>
                    <tr>
                        <td>待客台次</td>
                        <td>{stats_2025_april['total']:,}</td>
                        <td>{stats_2025_may['total']:,}</td>
                        <td>{stats_2026_april['total']:,}</td>
                        <td>{stats_2026_may['total']:,}</td>
                        <td class="{'growth-positive' if april_yoy_total >= 0 else 'growth-negative'}">
                            {f'+{april_yoy_total:,.0f}' if april_yoy_total >= 0 else f'{april_yoy_total:,.0f}'} ({april_yoy_total_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_yoy_total >= 0 else 'growth-negative'}">
                            {f'+{may_yoy_total:,.0f}' if may_yoy_total >= 0 else f'{may_yoy_total:,.0f}'} ({may_yoy_total_pct:+.1f}%)
                        </td>
                        <td class="{'growth-positive' if may_mom_total >= 0 else 'growth-negative'}">
                            {f'+{may_mom_total:,.0f}' if may_mom_total >= 0 else f'{may_mom_total:,.0f}'} ({may_mom_total_pct:+.1f}%)
                        </td>
                    </tr>
                </tbody>
            </table>
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
                        <th>总营业额</th>
                        <th>超市收入</th>
                        <th>房费收入</th>
                        <th>待客台数</th>
                    </tr>
                </thead>
                <tbody>
"""

# 4月数据
html_content += f"""
                    <tr style="background: #e6f0ff;">
                        <td colspan="6" style="font-weight: bold; color: #0066cc;">2026年4月数据</td>
                    </tr>
"""
for _, row in data_2026_april.iterrows():
    html_content += f"""
                    <tr>
                        <td>{row['data_date'].strftime('%Y-%m-%d')}</td>
                        <td>{row['weekday']}</td>
                        <td>¥{row['total_revenue']:,.0f}</td>
                        <td>¥{row['supermarket_revenue']:,.0f}</td>
                        <td>¥{row['room_revenue']:,.0f}</td>
                        <td>{row['customers']}台</td>
                    </tr>
"""

# 5月数据
html_content += f"""
                    <tr style="background: #fff3e6;">
                        <td colspan="6" style="font-weight: bold; color: #ea580c;">2026年5月数据</td>
                    </tr>
"""
for _, row in data_2026_may.iterrows():
    html_content += f"""
                    <tr>
                        <td>{row['data_date'].strftime('%Y-%m-%d')}</td>
                        <td>{row['weekday']}</td>
                        <td>¥{row['total_revenue']:,.0f}</td>
                        <td>¥{row['supermarket_revenue']:,.0f}</td>
                        <td>¥{row['room_revenue']:,.0f}</td>
                        <td>{row['customers']}台</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>
"""

# 生成洞察分析
insights = []
if diff_total > 0:
    insights.append(f"5月总营业额较4月增长 ¥{diff_total:,.0f} ({growth_rate:+.1f}%)，经营态势良好")
else:
    insights.append(f"5月总营业额较4月下降 ¥{abs(diff_total):,.0f} ({growth_rate:+.1f}%)，需关注")

if may_avg_customers > april_avg_customers:
    insights.append(f"日均待客台数从 {april_avg_customers:.1f}台 提升至 {may_avg_customers:.1f}台，获客能力增强")
else:
    insights.append(f"日均待客台数从 {april_avg_customers:.1f}台 下降至 {may_avg_customers:.1f}台，需关注客流情况")

if may_supermarket > april_supermarket:
    insights.append(f"超市收入增长，商品销售表现提升")
else:
    insights.append(f"超市收入有所下降，可优化商品策略")

if may_room > april_room:
    insights.append(f"房费收入增长，包厢利用率提升")
else:
    insights.append(f"房费收入有所下降，可关注包厢运营情况")

# 时段分析洞察
if april_yoy_total > 0:
    insights.append(f"4月同比分析：2026年4月总待客台次较2025年同期增长 {april_yoy_total:,.0f}台 ({april_yoy_total_pct:+.1f}%)")
else:
    insights.append(f"4月同比分析：2026年4月总待客台次较2025年同期下降 {abs(april_yoy_total):,.0f}台 ({april_yoy_total_pct:+.1f}%)")

if may_yoy_total > 0:
    insights.append(f"5月同比分析：2026年5月1-15日总待客台次较2025年同期增长 {may_yoy_total:,.0f}台 ({may_yoy_total_pct:+.1f}%)")
else:
    insights.append(f"5月同比分析：2026年5月1-15日总待客台次较2025年同期下降 {abs(may_yoy_total):,.0f}台 ({may_yoy_total_pct:+.1f}%)")

if may_mom_total > 0:
    insights.append(f"5月环比分析：较4月增长 {may_mom_total:,.0f}台 ({may_mom_total_pct:+.1f}%)")
else:
    insights.append(f"5月环比分析：较4月下降 {abs(may_mom_total):,.0f}台 ({may_mom_total_pct:+.1f}%)")

# 时段分析
april_total_period = april_before_18 + april_eight_to_twenty_four + april_after_zero
may_total_period = may_before_18 + may_eight_to_twenty_four + may_after_zero
if april_total_period > 0 and may_total_period > 0:
    april_night_ratio = (april_eight_to_twenty_four + april_after_zero) / april_total_period * 100
    may_night_ratio = (may_eight_to_twenty_four + may_after_zero) / may_total_period * 100
    if may_night_ratio > april_night_ratio:
        insights.append(f"晚场客流占比从 {april_night_ratio:.1f}% 提升到 {may_night_ratio:.1f}%，夜场经营改善")
    else:
        insights.append(f"晚场客流占比从 {april_night_ratio:.1f}% 下降到 {may_night_ratio:.1f}%，可关注夜场运营策略")

html_content += f"""
        <div class="section">
            <h2>核心洞察</h2>
            <div class="insights">
                <h3>关键发现</h3>
                <ul>
"""
for insight in insights:
    html_content += f"""
                    <li>{insight}</li>
"""

html_content += """
                </ul>
            </div>
        </div>
"""

# 图表数据
april_dates = [d.strftime('%m-%d') for d in data_2026_april['data_date']]
april_values = data_2026_april['total_revenue'].tolist()
may_dates = [d.strftime('%m-%d') for d in data_2026_may['data_date']]
may_values = data_2026_may['total_revenue'].tolist()

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

            // 收入结构图表
            new Chart(document.getElementById('revenueBreakdown'), {{
                type: 'bar',
                data: {{
                    labels: ['超市收入', '房费收入', '储值卡销售', '次卡销售'],
                    datasets: [
                        {{
                            label: '2026年4月',
                            data: [{april_supermarket}, {april_room}, {april_stored}, {april_times}],
                            backgroundColor: 'rgba(0,102,204,0.7)',
                            borderColor: '#0066cc',
                            borderWidth: 2
                        }},
                        {{
                            label: '2026年5月',
                            data: [{may_supermarket}, {may_room}, {may_stored}, {may_times}],
                            backgroundColor: 'rgba(234,88,12,0.7)',
                            borderColor: '#ea580c',
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
                    labels: {april_dates + may_dates},
                    datasets: [
                        {{
                            label: '日营业额',
                            data: {april_values + may_values},
                            borderColor: '#7c3aed',
                            backgroundColor: 'rgba(124, 58, 237, 0.1)',
                            tension: 0.3,
                            fill: true,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }}
                    ]
                }},
                options: {{
                    ...chartOptions,
                    plugins: {{
                        ...chartOptions.plugins
                    }}
                }}
            }});

            // 总待客台数
            new Chart(document.getElementById('customersTotal'), {{
                type: 'bar',
                data: {{
                    labels: ['总待客台数'],
                    datasets: [
                        {{
                            label: '2026年4月',
                            data: [{april_customers}],
                            backgroundColor: 'rgba(0,102,204,0.7)',
                            borderColor: '#0066cc',
                            borderWidth: 2
                        }},
                        {{
                            label: '2026年5月',
                            data: [{may_customers}],
                            backgroundColor: 'rgba(234,88,12,0.7)',
                            borderColor: '#ea580c',
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
                            label: '2026年4月',
                            data: [{april_avg_customers}],
                            backgroundColor: 'rgba(0,102,204,0.7)',
                            borderColor: '#0066cc',
                            borderWidth: 2
                        }},
                        {{
                            label: '2026年5月',
                            data: [{may_avg_customers}],
                            backgroundColor: 'rgba(234,88,12,0.7)',
                            borderColor: '#ea580c',
                            borderWidth: 2
                        }}
                    ]
                }},
                options: chartOptions
            }});

            // 时段分布
            new Chart(document.getElementById('timePeriod'), {{
                type: 'bar',
                data: {{
                    labels: ['18点前', '18-24点', '00点后'],
                    datasets: [
                        {{
                            label: '2026年4月',
                            data: [{april_before_18}, {april_eight_to_twenty_four}, {april_after_zero}],
                            backgroundColor: 'rgba(0,102,204,0.7)',
                            borderColor: '#0066cc',
                            borderWidth: 2
                        }},
                        {{
                            label: '2026年5月',
                            data: [{may_before_18}, {may_eight_to_twenty_four}, {may_after_zero}],
                            backgroundColor: 'rgba(234,88,12,0.7)',
                            borderColor: '#ea580c',
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
output_file = PROJECT_ROOT / "reports" / "chenyu_april_vs_may_comparison.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"\n✅ 对比报告已生成: {output_file}")
print(f"\n📊 报告要点:")
print(f"   • 2026年4月总营业额: ¥{april_total:,.0f} (日均 ¥{april_avg:,.0f})")
print(f"   • 2026年5月1-15日总营业额: ¥{may_total:,.0f} (日均 ¥{may_avg:,.0f})")
print(f"   • 5月较4月变化: {'+' if diff_total > 0 else ''}¥{diff_total:,.0f} ({growth_rate:+.1f}%)")
print(f"   • 待客台数: 2026年4月 {april_customers:,}台 vs 2026年5月1-15日 {may_customers:,}台")
print(f"\n📈 时段同比环比分析:")
april_yoy_text = f"+{april_yoy_total:,.0f}台" if april_yoy_total >= 0 else f"{april_yoy_total:,.0f}台"
may_yoy_text = f"+{may_yoy_total:,.0f}台" if may_yoy_total >= 0 else f"{may_yoy_total:,.0f}台"
may_mom_text = f"+{may_mom_total:,.0f}台" if may_mom_total >= 0 else f"{may_mom_total:,.0f}台"
print(f"   • 4月同比(较2025年4月): {april_yoy_text} ({april_yoy_total_pct:+.1f}%)")
print(f"   • 5月同比(较2025年5月1-15日): {may_yoy_text} ({may_yoy_total_pct:+.1f}%)")
print(f"   • 5月环比(较2026年4月): {may_mom_text} ({may_mom_total_pct:+.1f}%)")

print(f"\n📊 晚场客流占比计算:")
april_night_count = april_eight_to_twenty_four + april_after_zero
may_night_count = may_eight_to_twenty_four + may_after_zero
april_night_ratio = (april_night_count / april_total_period * 100) if april_total_period > 0 else 0
may_night_ratio = (may_night_count / may_total_period * 100) if may_total_period > 0 else 0
print(f"   • 4月: 晚场客流 {april_night_count:,} 台 / 总客流 {april_total_period:,} 台 = {april_night_ratio:.1f}%")
print(f"   • 5月: 晚场客流 {may_night_count:,} 台 / 总客流 {may_total_period:,} 台 = {may_night_ratio:.1f}%")
print(f"   • 变化: {may_night_ratio - april_night_ratio:+.1f}%")
print(f"\n📂 报告文件位置: {output_file}")
print(f"   请在浏览器中打开查看完整报告")