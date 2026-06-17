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

query_all_recharge = """
SELECT 
    s.store_name,
    sv.member_phone,
    sv.member_name,
    sv.member_level,
    sv.data_date as recharge_date,
    sv.stored_amount as recharge_principal,
    sv.payment_amount as payment_amount,
    sv.is_first_recharge,
    sv.total_balance as balance_after_recharge,
    sv.principal_balance as principal_after_recharge,
    sv.gift_balance as gift_after_recharge,
    sv.drink_principal,
    sv.room_principal,
    sv.marketing_manager
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE sv.data_date >= '2026-01-01' 
  AND sv.data_date <= '2026-02-28'
ORDER BY sv.data_date, s.store_name, sv.member_phone
"""

df_all_recharge = pd.read_sql(query_all_recharge, conn)

query_all_members = """
SELECT 
    sv.store_id,
    s.store_name,
    sv.member_phone,
    sv.member_name,
    sv.member_level,
    MIN(sv.data_date) as first_recharge_date,
    MAX(sv.data_date) as last_recharge_date,
    SUM(sv.stored_amount) as total_recharge_principal,
    SUM(sv.payment_amount) as total_payment_amount,
    COUNT(*) as recharge_count,
    SUM(CASE WHEN sv.is_first_recharge = 1 THEN 1 ELSE 0 END) as first_recharge_count,
    SUM(CASE WHEN sv.is_first_recharge = 0 THEN 1 ELSE 0 END) as repeat_recharge_count,
    sv.marketing_manager
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
WHERE sv.data_date >= '2026-01-01' 
  AND sv.data_date <= '2026-02-28'
GROUP BY sv.store_id, s.store_name, sv.member_phone, sv.member_name, 
         sv.member_level, sv.marketing_manager
"""

df_all_members = pd.read_sql(query_all_members, conn)

phones = df_all_members['member_phone'].unique().tolist()
phone_list = [str(p) for p in phones if p and str(p) != 'nan' and str(p).strip()]
phones_str = ','.join([f"'{p}'" for p in phone_list])

query_balance = """
SELECT 
    mb.member_phone,
    mb.member_name,
    mb.change_store,
    mb.change_time as latest_change_time,
    mb.principal_balance,
    mb.gift_balance,
    mb.principal_change,
    mb.gift_change,
    mb.change_type
FROM member_balance_change mb
WHERE mb.change_time = (
    SELECT MAX(change_time) 
    FROM member_balance_change mb2 
    WHERE mb2.member_phone = mb.member_phone
)
AND mb.member_phone IN ({phones})
""".format(phones=phones_str)

df_latest_balance = pd.read_sql(query_balance, conn)

df_final = df_all_members.merge(
    df_latest_balance[['member_phone', 'principal_balance', 'gift_balance', 'latest_change_time', 'change_store']], 
    on='member_phone', 
    how='left',
    suffixes=('_member', '_balance')
)

df_final['principal_consumed_calc'] = df_final['total_recharge_principal'] - df_final['principal_balance'].fillna(0)
df_final['consumption_rate'] = (df_final['principal_consumed_calc'] / df_final['total_recharge_principal'] * 100).round(1)

store_summary = df_final.groupby('store_name').agg(
    会员数=('member_phone', 'nunique'),
    总充值本金=('total_recharge_principal', 'sum'),
    总剩余本金=('principal_balance', 'sum'),
    总消耗本金=('principal_consumed_calc', 'sum'),
    平均充值次数=('recharge_count', 'mean'),
    复购人数=('repeat_recharge_count', lambda x: (x > 0).sum()),
).reset_index().sort_values('总充值本金', ascending=False)

store_summary['消耗比例'] = (store_summary['总消耗本金'] / store_summary['总充值本金'] * 100).round(1)
store_summary['复购率'] = (store_summary['复购人数'] / store_summary['会员数'] * 100).round(1)

total_recharge = df_final['total_recharge_principal'].sum()
total_consumed = df_final['principal_consumed_calc'].sum()
total_remaining = df_final['principal_balance'].sum()
avg_consumption_rate = df_final['consumption_rate'].mean()
total_members = len(df_final)

df_first = df_all_recharge[df_all_recharge['is_first_recharge'] == 1]
df_repeat = df_all_recharge[df_all_recharge['is_first_recharge'] == 0]

first_count = len(df_first)
repeat_count = len(df_repeat)
first_amount = df_first['recharge_principal'].sum()
repeat_amount = df_repeat['recharge_principal'].sum()

recharge_dist = df_final['recharge_count'].value_counts().sort_index()

conn.close()

REPO_DIR = PROJECT_ROOT / "reports"
REPO_DIR.mkdir(exist_ok=True)

store_names = store_summary['store_name'].tolist()
store_recharge = store_summary['总充值本金'].tolist()
store_consumed = store_summary['总消耗本金'].tolist()
store_remaining = store_summary['总剩余本金'].tolist()
store_consumption_rate = store_summary['消耗比例'].tolist()
store_repurchase_rate = store_summary['复购率'].tolist()
store_member_count = store_summary['会员数'].tolist()
store_avg_recharge = store_summary['平均充值次数'].tolist()

recharge_freq_counts = recharge_dist.values.tolist()
recharge_freq_labels = [f"{n}次" for n in recharge_dist.index.tolist()]

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026年1-2月储值卡会员消耗分析</title>
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
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
        .recharge-compare {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .recharge-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 25px;
            color: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .recharge-card h3 {{
            font-size: 1em;
            margin-bottom: 15px;
            opacity: 0.9;
        }}
        .recharge-card .amount {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .recharge-card .detail {{
            font-size: 0.9em;
            opacity: 0.85;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>2026年1-2月 储值卡会员消耗分析</h1>
            <p class="subtitle">数据期间：2026年1月1日 - 2月28日</p>
        </header>

        <div class="dashboard">
            <div class="card">
                <h3>总储值会员</h3>
                <div class="value">{total_members:,}人</div>
                <div class="label">1-2月参与储值</div>
            </div>
            <div class="card">
                <h3>总充值本金</h3>
                <div class="value">¥{total_recharge:,.0f}</div>
                <div class="label">首充+复充合计</div>
            </div>
            <div class="card">
                <h3>总已消耗</h3>
                <div class="value">¥{total_consumed:,.0f}</div>
                <div class="label">本金消耗合计</div>
            </div>
            <div class="card">
                <h3>总剩余本金</h3>
                <div class="value">¥{total_remaining:,.0f}</div>
                <div class="label">待消耗金额</div>
            </div>
            <div class="card">
                <h3>平均消耗比例</h3>
                <div class="value">{avg_consumption_rate:.1f}%</div>
                <div class="label">会员均值</div>
            </div>
        </div>

        <div class="section">
            <h2>首充 vs 复充对比</h2>
            <div class="recharge-compare">
                <div class="recharge-card">
                    <h3>💳 首次充值</h3>
                    <div class="amount">¥{first_amount:,.0f}</div>
                    <div class="detail">首充笔数：{first_count:,} 笔</div>
                    <div class="detail">首充会员：{df_first['member_phone'].nunique():,} 人</div>
                    <div class="detail">占比：{first_count/(first_count+repeat_count)*100:.1f}%</div>
                </div>
                <div class="recharge-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <h3>🔄 重复充值</h3>
                    <div class="amount">¥{repeat_amount:,.0f}</div>
                    <div class="detail">复充笔数：{repeat_count:,} 笔</div>
                    <div class="detail">复充会员：{df_repeat['member_phone'].nunique():,} 人</div>
                    <div class="detail">占比：{repeat_count/(first_count+repeat_count)*100:.1f}%</div>
                </div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h3>各门店总充值本金对比</h3>
                <canvas id="storeRechargeChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各门店消耗比例对比</h3>
                <canvas id="storeConsumptionChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>充值频次分布</h3>
                <canvas id="rechargeFreqChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>首充 vs 复充金额占比</h3>
                <canvas id="rechargeTypeChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各门店复购率对比</h3>
                <canvas id="repurchaseChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各门店会员数与平均充值次数</h3>
                <canvas id="memberChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>各门店详细统计</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>门店</th>
                        <th class="number">会员数</th>
                        <th class="number">总充值本金</th>
                        <th class="number">总消耗本金</th>
                        <th class="number">总剩余本金</th>
                        <th class="number">消耗比例</th>
                        <th class="number">平均充值次数</th>
                        <th class="number">复购率</th>
                    </tr>
                </thead>
                <tbody>
"""

for _, row in store_summary.iterrows():
    html_content += f"""
                    <tr>
                        <td>{row['store_name']}</td>
                        <td class="number">{row['会员数']:,}</td>
                        <td class="number">¥{row['总充值本金']:,.0f}</td>
                        <td class="number">¥{row['总消耗本金']:,.0f}</td>
                        <td class="number">¥{row['总剩余本金']:,.0f}</td>
                        <td class="number">{row['消耗比例']:.1f}%</td>
                        <td class="number">{row['平均充值次数']:.1f}</td>
                        <td class="number">{row['复购率']:.1f}%</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>会员明细 (Top 50)</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>门店</th>
                        <th>会员</th>
                        <th>手机号</th>
                        <th class="number">充值次数</th>
                        <th class="number">总充值本金</th>
                        <th class="number">已消耗</th>
                        <th class="number">剩余本金</th>
                        <th class="number">消耗比例</th>
                    </tr>
                </thead>
                <tbody>
"""

member_name_col = 'member_name_member' if 'member_name_member' in df_final.columns else 'member_name'

for _, row in df_final.head(50).iterrows():
    phone_display = str(row['member_phone'])[-4:] if row['member_phone'] else ''
    principal_bal = row['principal_balance'] if pd.notna(row['principal_balance']) else 0
    rate = row['consumption_rate'] if pd.notna(row['consumption_rate']) else 0
    html_content += f"""
                    <tr>
                        <td>{row['store_name']}</td>
                        <td>{str(row[member_name_col])[:8]}</td>
                        <td>{phone_display}</td>
                        <td class="number">{int(row['recharge_count'])}</td>
                        <td class="number">¥{row['total_recharge_principal']:,.0f}</td>
                        <td class="number">¥{row['principal_consumed_calc']:,.0f}</td>
                        <td class="number">¥{principal_bal:,.0f}</td>
                        <td class="number">{rate:.1f}%</td>
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

        new Chart(document.getElementById('storeRechargeChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [{
                    label: '总充值本金',
                    data: """ + json.dumps(store_recharge) + """,
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderWidth: 2
                }]
            },
            options: chartOptions
        });

        new Chart(document.getElementById('storeConsumptionChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [{
                    label: '消耗比例 (%)',
                    data: """ + json.dumps(store_consumption_rate) + """,
                    backgroundColor: 'rgba(240, 147, 251, 0.7)',
                    borderWidth: 2
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    ...chartOptions.scales,
                    y: { ...chartOptions.scales.y, beginAtZero: true, max: 100 }
                }
            }
        });

        new Chart(document.getElementById('rechargeFreqChart'), {
            type: 'pie',
            data: {
                labels: """ + json.dumps(recharge_freq_labels, ensure_ascii=False) + """,
                datasets: [{
                    data: """ + json.dumps(recharge_freq_counts) + """,
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(240, 147, 251, 0.8)',
                        'rgba(245, 87, 108, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(79, 172, 254, 0.8)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#1a1a1a' } }
                }
            }
        });

        new Chart(document.getElementById('rechargeTypeChart'), {
            type: 'doughnut',
            data: {
                labels: ['首次充值', '重复充值'],
                datasets: [{
                    data: [""" + f"{first_amount}, {repeat_amount}" + """],
                    backgroundColor: ['rgba(102, 126, 234, 0.8)', 'rgba(240, 147, 251, 0.8)'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#1a1a1a' } }
                }
            }
        });

        new Chart(document.getElementById('repurchaseChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [{
                    label: '复购率 (%)',
                    data: """ + json.dumps(store_repurchase_rate) + """,
                    backgroundColor: 'rgba(79, 172, 254, 0.7)',
                    borderWidth: 2
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    ...chartOptions.scales,
                    y: { ...chartOptions.scales.y, beginAtZero: true, max: 100 }
                }
            }
        });

        new Chart(document.getElementById('memberChart'), {
            type: 'bar',
            data: {
                labels: """ + json.dumps(store_names, ensure_ascii=False) + """,
                datasets: [
                    {
                        label: '会员数',
                        data: """ + json.dumps(store_member_count) + """,
                        backgroundColor: 'rgba(102, 126, 234, 0.7)',
                        borderWidth: 2,
                        yAxisID: 'y'
                    },
                    {
                        label: '平均充值次数',
                        data: """ + json.dumps(store_avg_recharge) + """,
                        backgroundColor: 'rgba(240, 147, 251, 0.7)',
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#1a1a1a' } }
                },
                scales: {
                    x: { ticks: { color: '#1a1a1a' }, grid: { color: 'rgba(0,0,0,0.05)' } },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: { color: '#1a1a1a' },
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        title: { display: true, text: '会员数', color: '#1a1a1a' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        ticks: { color: '#1a1a1a' },
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: '平均充值次数', color: '#1a1a1a' }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""

output_file = REPO_DIR / "jan_feb_stored_card_visual_report.html"
with open(output_file, 'w', encoding='utf-8-sig') as f:
    f.write(html_content)

print(f"\n✅ 可视化报表已生成: {output_file}")
print(f"\n📊 请在浏览器中打开查看完整报表")
