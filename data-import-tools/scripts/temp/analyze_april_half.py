#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pymysql
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def get_order_data(store_id, start_date, end_date):
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    sql = """
    SELECT * FROM order_detail 
    WHERE store_id = %s 
    AND data_date BETWEEN %s AND %s
    ORDER BY open_time
    """
    cursor.execute(sql, (store_id, start_date, end_date))
    orders = cursor.fetchall()
    
    # 筛选出0:00-6:00的订单
    midnight_orders = []
    for order in orders:
        if order['open_time']:
            hour = order['open_time'].hour
            if 0 <= hour < 6:
                midnight_orders.append(order)
    
    cursor.close()
    return midnight_orders

def analyze_orders(orders):
    stats = {
        'total': len(orders),
        'member': 0,
        'guest': 0,
        'amount': 0,
        'zero_amount': 0,
        'hour_distribution': defaultdict(int),
        'member_list': [],
        'guest_list': []
    }
    
    for order in orders:
        hour = order['open_time'].hour
        stats['hour_distribution'][hour] += 1
        
        member = bool(order['customer_phone'] and order['customer_phone'].strip())
        amount = float(order['actual_amount'] or 0)
        
        if member:
            stats['member'] += 1
            stats['member_list'].append(order)
        else:
            stats['guest'] += 1
            stats['guest_list'].append(order)
        
        stats['amount'] += amount
        if amount == 0:
            stats['zero_amount'] += 1
    
    return stats

conn = pymysql.connect(**MYSQL_CONFIG)

print("=" * 80)
print("4月上半月 vs 下半月对比分析")
print("=" * 80)

stores = {1: '鸡西店', 8: '安达店', 11: '通化店'}

# 收集所有数据用于HTML生成
all_data = {}

for store_id, store_name in stores.items():
    print(f"\n{'-'*80}")
    print(f"{store_name}")
    print('-'*80)
    
    # 上半月：4月1-15日
    first_half_orders = get_order_data(store_id, '2026-04-01', '2026-04-15')
    first_half_stats = analyze_orders(first_half_orders)
    
    # 下半月：4月16-30日
    second_half_orders = get_order_data(store_id, '2026-04-16', '2026-04-30')
    second_half_stats = analyze_orders(second_half_orders)
    
    all_data[store_name] = {
        'first_half': first_half_stats,
        'second_half': second_half_stats,
        'first_half_orders': first_half_orders,
        'second_half_orders': second_half_orders
    }
    
    print(f"\n【上半月（4.1-4.15）】")
    print(f"总订单数: {first_half_stats['total']}")
    print(f"会员订单: {first_half_stats['member']}")
    print(f"散客订单: {first_half_stats['guest']}")
    print(f"0元订单: {first_half_stats['zero_amount']}")
    print(f"总金额: ¥{first_half_stats['amount']:.2f}")
    print(f"时段分布: {dict(first_half_stats['hour_distribution'])}")
    
    print(f"\n【下半月（4.16-4.30）】")
    print(f"总订单数: {second_half_stats['total']}")
    print(f"会员订单: {second_half_stats['member']}")
    print(f"散客订单: {second_half_stats['guest']}")
    print(f"0元订单: {second_half_stats['zero_amount']}")
    print(f"总金额: ¥{second_half_stats['amount']:.2f}")
    print(f"时段分布: {dict(second_half_stats['hour_distribution'])}")

conn.close()

# 生成HTML报告
html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4月上半月 vs 下半月对比分析</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center; padding: 40px 20px; margin-bottom: 40px;
            background: rgba(255,255,255,0.05); border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            font-size: 2.5em; margin-bottom: 10px;
            background: linear-gradient(45deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .dashboard {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-bottom: 40px;
        }
        .card {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1); transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 { font-size: 1em; color: #a0a0a0; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }
        .card .value { font-size: 2.2em; font-weight: bold; margin-bottom: 10px; }
        .chart-container {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;
        }
        .chart-container h2 { margin-bottom: 20px; color: #00d4ff; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 30px; }
        .store-section {
            background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px;
            border: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;
        }
        .store-section h2 { margin-bottom: 25px; color: #00d4ff; }
        .store-tabs { display: flex; gap: 10px; margin-bottom: 25px; flex-wrap: wrap; }
        .store-tab {
            padding: 12px 25px; background: rgba(255,255,255,0.1); border: none;
            border-radius: 10px; color: #fff; cursor: pointer; transition: all 0.3s; font-size: 1em;
        }
        .store-tab:hover { background: rgba(255,255,255,0.2); }
        .store-tab.active { background: linear-gradient(45deg, #00d4ff, #7b2cbf); }
        .half-tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .half-tab {
            padding: 10px 20px; background: rgba(255,255,255,0.1); border: none;
            border-radius: 8px; color: #fff; cursor: pointer; transition: all 0.3s;
        }
        .half-tab:hover { background: rgba(255,255,255,0.2); }
        .half-tab.active { background: linear-gradient(45deg, #4ade80, #22c55e); }
        .orders-table {
            width: 100%; border-collapse: collapse; font-size: 0.9em;
        }
        .orders-table th, .orders-table td {
            padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .orders-table th { background: rgba(0,0,0,0.2); font-weight: 600; color: #00d4ff; }
        .orders-table tr:hover { background: rgba(255,255,255,0.05); }
        .zero-amount { color: #ff6b6b; font-weight: bold; }
        .member-badge {
            display: inline-block; padding: 4px 12px;
            background: linear-gradient(45deg, #00d4ff, #7b2cbf);
            border-radius: 20px; font-size: 0.85em;
        }
        .summary-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;
            margin-bottom: 25px;
        }
        .summary-item {
            background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .summary-item .label { color: #a0a0a0; font-size: 0.9em; margin-bottom: 8px; }
        .summary-item .value { font-size: 1.5em; font-weight: bold; }
        .highlight { color: #ff6b6b; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 4月上半月 vs 下半月对比分析</h1>
            <p style="color:#a0a0a0; font-size:1.1em">鸡西店 · 安达店 · 通化店</p>
        </header>
"""

# 计算总体数据
total_first = sum([data['first_half']['total'] for data in all_data.values()])
total_second = sum([data['second_half']['total'] for data in all_data.values()])
member_first = sum([data['first_half']['member'] for data in all_data.values()])
member_second = sum([data['second_half']['member'] for data in all_data.values()])
zero_first = sum([data['first_half']['zero_amount'] for data in all_data.values()])
zero_second = sum([data['second_half']['zero_amount'] for data in all_data.values()])
amount_first = sum([data['first_half']['amount'] for data in all_data.values()])
amount_second = sum([data['second_half']['amount'] for data in all_data.values()])

html_content += f"""
        <div class="dashboard">
            <div class="card">
                <h3>总订单数（上半月）</h3>
                <div class="value" style="color:#00d4ff">{total_first}</div>
            </div>
            <div class="card">
                <h3>总订单数（下半月）</h3>
                <div class="value" style="color:#7b2cbf">{total_second}</div>
            </div>
            <div class="card">
                <h3>会员订单占比（上半月）</h3>
                <div class="value" style="color:#4ade80">{(member_first/total_first*100):.1f}%</div>
            </div>
            <div class="card">
                <h3>会员订单占比（下半月）</h3>
                <div class="value" style="color:#fb923c">{(member_second/total_second*100):.1f}%</div>
            </div>
            <div class="card">
                <h3>0元订单数（上半月）</h3>
                <div class="value" style="color:#ef4444">{zero_first}</div>
            </div>
            <div class="card">
                <h3>0元订单数（下半月）</h3>
                <div class="value" style="color:#ef4444">{zero_second}</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h2>各门店订单数对比</h2>
                <canvas id="ordersChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>各门店消费金额对比</h2>
                <canvas id="amountChart"></canvas>
            </div>
"""

# 生成门店详情
for store_name, store_data in all_data.items():
    html_content += f"""
        <div class="store-section">
            <h2>🎯 {store_name}</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">上半月订单数</div>
                    <div class="value">{store_data['first_half']['total']}</div>
                </div>
                <div class="summary-item">
                    <div class="label">下半月订单数</div>
                    <div class="value">{store_data['second_half']['total']}</div>
                </div>
                <div class="summary-item">
                    <div class="label">上半月0元订单</div>
                    <div class="value highlight">{store_data['first_half']['zero_amount']}</div>
                </div>
                <div class="summary-item">
                    <div class="label">下半月0元订单</div>
                    <div class="value highlight">{store_data['second_half']['zero_amount']}</div>
                </div>
                <div class="summary-item">
                    <div class="label">上半月金额</div>
                    <div class="value">¥{store_data['first_half']['amount']:.0f}</div>
                </div>
                <div class="summary-item">
                    <div class="label">下半月金额</div>
                    <div class="value">¥{store_data['second_half']['amount']:.0f}</div>
                </div>
            </div>
            <div class="half-tabs">
                <button class="half-tab active" onclick="showHalf('{store_name}', 'first')">上半月（4.1-4.15）</button>
                <button class="half-tab" onclick="showHalf('{store_name}', 'second')">下半月（4.16-4.30）</button>
            </div>
            <div id="{store_name}-first" class="order-table-container">
                <table class="orders-table">
                    <thead>
                        <tr>
                            <th>开房时间</th><th>包厢号</th><th>开房人</th><th>手机号</th><th>是否会员</th><th>实收金额</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    # 添加上半月订单
    for order in store_data['first_half_orders']:
        open_time = order['open_time'].strftime('%Y-%m-%d %H:%M') if order['open_time'] else ''
        room_no = order['room_no'] or ''
        customer_name = order['customer_name'] or ''
        customer_phone = order['customer_phone'] or ''
        member = bool(customer_phone and customer_phone.strip())
        amount = float(order['actual_amount'] or 0)
        amount_class = ' class="zero-amount"' if amount == 0 else ''
        html_content += f"""
                        <tr>
                            <td>{open_time}</td>
                            <td>{room_no}</td>
                            <td>{customer_name}</td>
                            <td>{customer_phone}</td>
                            <td><span class="member-badge">{ '会员' if member else '散客' }</span></td>
                            <td{amount_class}>¥{amount:.2f}</td>
                        </tr>
"""
    
    html_content += """
                    </tbody>
                </table>
            </div>
"""
    
    html_content += f"""
            <div id="{store_name}-second" class="order-table-container" style="display:none">
                <table class="orders-table">
                    <thead>
                        <tr>
                            <th>开房时间</th><th>包厢号</th><th>开房人</th><th>手机号</th><th>是否会员</th><th>实收金额</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    # 添加下半月订单
    for order in store_data['second_half_orders']:
        open_time = order['open_time'].strftime('%Y-%m-%d %H:%M') if order['open_time'] else ''
        room_no = order['room_no'] or ''
        customer_name = order['customer_name'] or ''
        customer_phone = order['customer_phone'] or ''
        member = bool(customer_phone and customer_phone.strip())
        amount = float(order['actual_amount'] or 0)
        amount_class = ' class="zero-amount"' if amount == 0 else ''
        html_content += f"""
                        <tr>
                            <td>{open_time}</td>
                            <td>{room_no}</td>
                            <td>{customer_name}</td>
                            <td>{customer_phone}</td>
                            <td><span class="member-badge">{ '会员' if member else '散客' }</span></td>
                            <td{amount_class}>¥{amount:.2f}</td>
                        </tr>
"""
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
"""

# 添加图表数据
html_content += """
        <script>
            function showHalf(store, half) {
                // 更新按钮样式
                const container = event.target.closest('.store-section');
                container.querySelectorAll('.half-tab').forEach(tab => tab.classList.remove('active'));
                event.target.classList.add('active');
                
                // 切换表格显示
                document.getElementById(store + '-first').style.display = 'none';
                document.getElementById(store + '-second').style.display = 'none';
                document.getElementById(store + '-' + half).style.display = 'block';
            }
            
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
            
            new Chart(document.getElementById('ordersChart'), {
                type: 'bar',
                data: {
                    labels: ['鸡西店', '安达店', '通化店'],
                    datasets: [
                        {
                            label: '上半月',
                            data: [""" + str(all_data['鸡西店']['first_half']['total']) + """, """ + str(all_data['安达店']['first_half']['total']) + """, """ + str(all_data['通化店']['first_half']['total']) + """],
                            backgroundColor: 'rgba(0,212,255,0.7)',
                            borderColor: '#00d4ff',
                            borderWidth: 2
                        },
                        {
                            label: '下半月',
                            data: [""" + str(all_data['鸡西店']['second_half']['total']) + """, """ + str(all_data['安达店']['second_half']['total']) + """, """ + str(all_data['通化店']['second_half']['total']) + """],
                            backgroundColor: 'rgba(123,44,191,0.7)',
                            borderColor: '#7b2cbf',
                            borderWidth: 2
                        }
                    ]
                },
                options: chartOptions
            });
            
            new Chart(document.getElementById('amountChart'), {
                type: 'bar',
                data: {
                    labels: ['鸡西店', '安达店', '通化店'],
                    datasets: [
                        {
                            label: '上半月',
                            data: [""" + str(int(all_data['鸡西店']['first_half']['amount'])) + """, """ + str(int(all_data['安达店']['first_half']['amount'])) + """, """ + str(int(all_data['通化店']['first_half']['amount'])) + """],
                            backgroundColor: 'rgba(74,222,128,0.7)',
                            borderColor: '#4ade80',
                            borderWidth: 2
                        },
                        {
                            label: '下半月',
                            data: [""" + str(int(all_data['鸡西店']['second_half']['amount'])) + """, """ + str(int(all_data['安达店']['second_half']['amount'])) + """, """ + str(int(all_data['通化店']['second_half']['amount'])) + """],
                            backgroundColor: 'rgba(251,146,60,0.7)',
                            borderColor: '#fb923c',
                            borderWidth: 2
                        }
                    ]
                },
                options: chartOptions
            });
        </script>
    </div>
</body>
</html>
"""

# 保存HTML文件
with open('/Users/ann/Desktop/AI/Project/数据导入/april_comparison.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("\n" + "=" * 80)
print("分析完成！报告已生成：april_comparison.html")
print("=" * 80)
