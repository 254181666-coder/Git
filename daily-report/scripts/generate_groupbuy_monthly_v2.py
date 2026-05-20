
#!/usr/bin/env python3
"""
团购月度分析报告生成脚本 - V2 版
使用store_daily表的数据，数据更准确
分析近一个月各门店团购套餐销售趋势，判断门店类型变化
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.database import query

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

STORE_NAME_MERGE = {
    '上东': '上东', '上东店': '上东',
    '临河街': None, '临河街店': None,
    '总部': None, '总部店': None,
    '晨宇': '晨宇', '晨宇店': '晨宇',
    '通辽': '通辽', '通辽店': '通辽',
    '松原一': '松原一', '松原一店': '松原一',
    '松原二': '松原二', '松原二店': '松原二',
    '佳木斯': '佳木斯', '佳木斯店': '佳木斯',
    '鸡西': '鸡西', '鸡西店': '鸡西',
    '红旗街': '红旗街', '红旗街店': '红旗街',
    '安达': '安达', '安达店': '安达',
    '榆树': '榆树', '榆树店': '榆树',
    '法库': '法库', '法库店': '法库',
    '通化': '通化', '通化店': '通化',
}

GB_SOURCES = {'抖音', '美团大众', '线下团购'}


def unify(n):
    if not n:
        return None
    return STORE_NAME_MERGE.get(str(n).strip(), str(n).strip())


def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))


def to_period(ot):
    if pd.isna(ot):
        return None
    h = ot.hour
    if 9 <= h < 18:
        return '日场'
    elif 18 <= h < 24:
        return '晚场'
    else:
        return '午夜场'


def load_monthly_data(start_date, end_date):
    sm = store_map()

    # 从store_daily表加载日营业数据（准确的营收数据）
    sd = query("""
        SELECT store_id, data_date, actual_amount, online_groupbuy
        FROM store_daily
        WHERE data_date >= %s AND data_date <= %s
    """, (start_date, end_date))

    if sd.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    sd['门店'] = sd['store_id'].map(sm).apply(unify)
    sd = sd[sd['门店'].notna()]
    sd = sd.rename(columns={
        'actual_amount': '总营收',
        'online_groupbuy': '团购营收'
    })

    # 从order_detail表加载订单明细（用于统计订单数、套餐明细）
    od = query("""
        SELECT store_id, data_date, order_no, open_time, source_channel,
               actual_amount, should_amount, order_type, room_no
        FROM order_detail
        WHERE data_date >= %s AND data_date <= %s
          AND order_type IN ('开房单', '点单')
    """, (start_date, end_date))

    psd = query("""
        SELECT store_id, data_date, room_no, package, product_name,
               quantity, sales_amount
        FROM product_sales_detail
        WHERE data_date >= %s AND data_date <= %s
          AND order_type IN ('开房单', '点单', '开房套餐')
          AND (package LIKE '%%团购%%' OR package LIKE '%%套餐%%')
    """, (start_date, end_date))

    if not od.empty:
        od['门店'] = od['store_id'].map(sm).apply(unify)
        od = od[od['门店'].notna()]
        od['is_groupbuy'] = od['source_channel'].isin(GB_SOURCES).astype(int)
        od['time_period'] = od['open_time'].apply(to_period)

    if not psd.empty:
        psd['门店'] = psd['store_id'].map(sm).apply(unify)
        psd = psd[psd['门店'].notna()]

    return sd, od, psd


def build_daily_stats(sd_df, od_df):
    # 使用store_daily的数据作为基准，用order_detail统计订单数
    daily_sd = sd_df.groupby(['data_date', '门店']).agg(
        总营收=('总营收', 'sum'),
        团购营收=('团购营收', 'sum')
    ).reset_index()
    
    if not od_df.empty:
        daily_od = od_df.groupby(['data_date', '门店']).agg(
            总订单=('order_no', 'nunique'),
            团购订单=('is_groupbuy', 'sum')
        ).reset_index()
        
        # 合并数据
        daily = pd.merge(daily_sd, daily_od, 
                        left_on=['data_date', '门店'],
                        right_on=['data_date', '门店'],
                        how='left')
        daily['总订单'] = daily['总订单'].fillna(0).astype(int)
        daily['团购订单'] = daily['团购订单'].fillna(0).astype(int)
    else:
        daily = daily_sd
        daily['总订单'] = 0
        daily['团购订单'] = 0
    
    return daily


def build_monthly_summary(sd_df, od_df):
    # 使用store_daily的数据
    summary_sd = sd_df.groupby('门店').agg(
        营业天数=('data_date', 'nunique'),
        总营收=('总营收', 'sum'),
        团购营收=('团购营收', 'sum')
    ).reset_index()
    
    if not od_df.empty:
        summary_od = od_df.groupby('门店').agg(
            总订单=('order_no', 'nunique'),
            团购订单=('is_groupbuy', 'sum')
        ).reset_index()
        
        summary = pd.merge(summary_sd, summary_od,
                          left_on='门店',
                          right_on='门店',
                          how='left')
        summary['总订单'] = summary['总订单'].fillna(0).astype(int)
        summary['团购订单'] = summary['团购订单'].fillna(0).astype(int)
    else:
        summary = summary_sd
        summary['总订单'] = 0
        summary['团购订单'] = 0
    
    # 计算团购占比（用营收计算更准确）
    summary['团购占比'] = np.where(
        summary['总营收'] > 0,
        (summary['团购营收'] / summary['总营收'] * 100).round(1),
        0
    )
    summary['日均订单'] = np.where(
        summary['营业天数'] > 0,
        (summary['总订单'] / summary['营业天数']).round(0).astype(int),
        0
    )
    summary['日均团购'] = np.where(
        summary['营业天数'] > 0,
        (summary['团购订单'] / summary['营业天数']).round(0).astype(int),
        0
    )

    def classify(r):
        if r['团购占比'] >= 70:
            return '团购店'
        if r['团购占比'] >= 30:
            return '混合型'
        return '消费型'

    summary['门店类型'] = summary.apply(classify, axis=1)
    return summary.sort_values('团购占比', ascending=False)


def build_period_stats(od_df):
    if od_df.empty:
        return pd.DataFrame()
    
    period = od_df.groupby(['门店', 'time_period']).agg(
        总订单=('order_no', 'nunique'),
        团购订单=('is_groupbuy', 'sum')
    ).reset_index()
    period['团购占比'] = np.where(
        period['总订单'] > 0,
        (period['团购订单'] / period['总订单'] * 100).round(1),
        0
    )
    return period


def build_package_stats(od_df, psd):
    if od_df.empty:
        return pd.DataFrame()
    
    gb_orders = od_df[od_df['is_groupbuy'] == 1].copy()
    
    if gb_orders.empty:
        return pd.DataFrame()

    pkg_list = []
    pkg_product_quantities = {}
    
    if not psd.empty:
        # 先建立订单到套餐的准确映射
        order_to_packages = {}
        for (data_date, store_id, room_no, pkg_name), group in psd.groupby(['data_date', 'store_id', 'room_no', 'package']):
            if pd.isna(pkg_name) or str(pkg_name).strip() == '':
                continue
            key = (data_date, store_id, str(room_no) if pd.notna(room_no) else '')
            if key not in order_to_packages:
                order_to_packages[key] = {}
            order_to_packages[key][pkg_name] = group
            
            # 同时收集商品数量信息
            store_unified = od_df[od_df['store_id'] == store_id]['门店'].iloc[0] if len(od_df[od_df['store_id'] == store_id]) > 0 else ''
            if not store_unified:
                continue
                
            pkg_key = (store_unified, pkg_name)
            if pkg_key not in pkg_product_quantities:
                pkg_product_quantities[pkg_key] = {}
                
            for product_name in group['product_name'].dropna().unique():
                prod_group = group[group['product_name'] == product_name]
                try:
                    qty_val = prod_group['quantity'].iloc[0] if 'quantity' in prod_group.columns else 1
                except Exception:
                    qty_val = 1
                
                try:
                    qty_int = int(qty_val) if qty_val == int(qty_val) else round(float(qty_val), 1)
                except (ValueError, TypeError):
                    qty_int = round(float(qty_val), 1) if qty_val else 1
                
                if product_name not in pkg_product_quantities[pkg_key]:
                    pkg_product_quantities[pkg_key][product_name] = []
                pkg_product_quantities[pkg_key][product_name].append(qty_int)

        # 遍历订单，准确匹配套餐
        for _, order in gb_orders.iterrows():
            store = order['门店']
            store_id = order['store_id']
            data_date = order['data_date']
            room_no = order['room_no'] if pd.notna(order['room_no']) else ''
            actual_amount = order['actual_amount']
            should_amount = order['should_amount']
            
            # 用准确的键查找套餐
            key = (data_date, store_id, str(room_no))
            pkg_name = None
            
            if key in order_to_packages:
                pkgs_dict = order_to_packages[key]
                if len(pkgs_dict) > 0:
                    if len(pkgs_dict) == 1:
                        pkg_name = next(iter(pkgs_dict.keys()))
                    else:
                        # 多个套餐，尝试用价格智能匹配
                        best_match_pkg = None
                        best_diff = float('inf')
                        for candidate_pkg, _ in pkgs_dict.items():
                            import re
                            numbers = re.findall(r'\d+\.?\d*', candidate_pkg)
                            for num_str in numbers:
                                try:
                                    pkg_price = float(num_str)
                                    diff = abs(pkg_price - should_amount)
                                    if diff < 10 and diff < best_diff:
                                        best_diff = diff
                                        best_match_pkg = candidate_pkg
                                except ValueError:
                                    continue
                        
                        if best_match_pkg:
                            pkg_name = best_match_pkg
                        else:
                            pkg_name = next(iter(pkgs_dict.keys()))
            
            if not pkg_name:
                pkg_name = f"{order['source_channel']}团购"

            pkg_list.append({
                '门店': store,
                'package': pkg_name,
                '销售数量': 1,
                '销售金额': actual_amount,
                '应收金额': should_amount
            })
    else:
        for _, order in gb_orders.iterrows():
            pkg_list.append({
                '门店': order['门店'],
                'package': f"{order['source_channel']}团购",
                '销售数量': 1,
                '销售金额': order['actual_amount'],
                '应收金额': order['should_amount']
            })

    if not pkg_list:
        return pd.DataFrame()

    pkg_df = pd.DataFrame(pkg_list)
    
    # 进一步过滤
    import re
    
    def filter_pkg_order(row):
        pkg_name = row['package']
        should_amount = row['应收金额']
        
        numbers = re.findall(r'\d+\.?\d*', pkg_name)
        
        if not numbers:
            return True
        
        for num_str in numbers:
            try:
                pkg_price = float(num_str)
                if abs(pkg_price - should_amount) < 10:
                    return True
            except ValueError:
                continue
        
        if '团购' in pkg_name and len(numbers) == 0:
            return True
        
        if '开机' in pkg_name:
            return True
        
        return False
    
    pkg_df['keep'] = pkg_df.apply(filter_pkg_order, axis=1)
    pkg_df = pkg_df[pkg_df['keep']].drop(columns=['keep'])
    
    def get_pkg_config(row):
        from collections import Counter
        
        store = row['门店']
        pkg = row['package']
        key = (store, pkg)
        
        if key not in pkg_product_quantities or not pkg_product_quantities[key]:
            return ''
        
        result = []
        for product_name, quantities in pkg_product_quantities[key].items():
            counter = Counter(quantities)
            most_common_qty = counter.most_common(1)[0][0]
            
            result.append(f"{product_name}*{most_common_qty}")
        
        result.sort(key=lambda x: x.split('*')[1], reverse=True)
        return ', '.join(result[:15]) + ('...' if len(result) > 15 else '')

    pkgs = pkg_df.groupby(['门店', 'package']).agg(
        销售数量=('销售数量', 'sum'),
        销售金额=('销售金额', 'sum'),
        应收金额=('应收金额', 'sum')
    ).reset_index()
    
    pkgs['包含商品'] = pkgs.apply(get_pkg_config, axis=1)
    pkgs['单价'] = (pkgs['销售金额'] / pkgs['销售数量']).round(2)
    
    return pkgs.sort_values(['门店', '销售金额'], ascending=[True, False])


def svg_trend_line(values, dates, width=500, height=120, color='#3498db', label=''):
    if len(values) < 2:
        return f'<span style="color:#999;font-size:11px">数据不足({len(values)}条)</span>'

    vs = [float(v) for v in values]
    vmin, vmax = min(vs), max(vs)
    rng = vmax - vmin or 1
    pad_left, pad_right, pad_top, pad_bot = 5, 5, 15, 20
    w, h = width - pad_left - pad_right, height - pad_top - pad_bot
    n = len(vs) - 1

    pts = []
    for i, v in enumerate(vs):
        x = pad_left + (i / n) * w if n > 0 else pad_left + w / 2
        y = pad_top + (1 - (v - vmin) / rng) * h
        pts.append((x, y))

    polyline = ' '.join(f"{x:.1f},{y:.1f}" for x, y in pts)
    fill_poly = f'{pts[0][0]:.1f},{pts[0][1]:.1f} {polyline} {pts[-1][0]:.1f},{pad_top + h:.1f} {pts[0][0]:.1f},{pad_top + h:.1f}'

    y_labels = ''
    for pct in [0, 50, 100]:
        y = pad_top + (1 - pct / 100) * h if rng > 0 else pad_top
        y_labels += f'<text x="2" y="{y+4:.0f}" font-size="8" fill="#999">{pct}%</text>'

    label_interval = max(1, len(dates) // 5)
    x_labels_html = ''
    for i in range(0, len(dates), label_interval):
        lbl = str(dates[i])[-5:]
        x_labels_html += f'<text x="{pts[i][0]:.0f}" y="{height-3}" font-size="8" fill="#999" text-anchor="middle">{lbl}</text>'

    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="display:block">
<rect width="{width}" height="{height}" fill="#fafafa" rx="4"/>
{y_labels}
<line x1="0" y1="{pad_top+h}" x2="{width}" y2="{pad_top+h}" stroke="#ddd" stroke-width="0.5"/>
<polygon points="{fill_poly}" fill="{color}" opacity="0.08"/>
<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{color}"/>
<text x="{width-5}" y="12" font-size="10" fill="{color}" text-anchor="end" font-weight="bold">{vs[-1]:.1f}%</text>
{x_labels_html}
</svg>'''


def generate_monthly_report(start_date=None, end_date=None, days=30):
    if end_date is None:
        end_date = date.today()
    else:
        end_date = pd.to_datetime(end_date).date()
    if start_date is None:
        start_date = end_date - timedelta(days=days - 1)
    else:
        start_date = pd.to_datetime(start_date).date()

    sd_df, od_df, psd = load_monthly_data(str(start_date), str(end_date))
    if sd_df.empty:
        print(f"❌ {start_date} ~ {end_date} 无数据")
        return None

    daily = build_daily_stats(sd_df, od_df)
    summary = build_monthly_summary(sd_df, od_df)
    period = build_period_stats(od_df)
    pkgs = build_package_stats(od_df, psd)

    stores_list = summary['门店'].tolist()
    all_dates = sorted(daily['data_date'].unique())

    total_stores = summary['门店'].nunique()
    total_orders = summary['总订单'].sum()
    total_gb = summary['团购订单'].sum()
    total_rev = summary['总营收'].sum()
    total_gb_rev = summary['团购营收'].sum()
    gb_ratio = (total_gb_rev / total_rev * 100) if total_rev > 0 else 0

    gb_stores = summary[summary['门店类型'] == '团购店']
    mix_stores = summary[summary['门店类型'] == '混合型']
    consume_stores = summary[summary['门店类型'] == '消费型']

    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>团购月度分析报告 - {start_date} ~ {end_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; 
                 color: #333; background: #f5f5f5; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: #fff; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #34495e; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #3498db; padding-left: 10px; }}
        h3 {{ color: #4a6fa5; margin-top: 25px; margin-bottom: 12px; background: #f8f9fa; padding: 10px 15px; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }}
        th {{ background: #f0f8ff; font-weight: 600; white-space: nowrap; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        tr:hover {{ background: #f0f0f0; }}
        .summary-box {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .card {{ background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 18px; border-radius: 8px; text-align: center; }}
        .card.green {{ background: linear-gradient(135deg, #11998e, #38ef7d); }}
        .card.orange {{ background: linear-gradient(135deg, #f093fb, #f5576c); }}
        .card.blue {{ background: linear-gradient(135deg, #4facfe, #00f2fe); }}
        .card h4 {{ margin: 0 0 8px 0; font-size: 13px; opacity: 0.9; }}
        .card .value {{ font-size: 26px; font-weight: bold; }}
        .pos {{ color: #28a745; font-weight: bold; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 团购月度分析报告 - {start_date} ~ {end_date}</h1>
        <div style="color:#7f8c8d;margin-bottom:15px">
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
            <span style="color:#3498db;font-weight:bold">使用store_daily表数据，数据更准确！</span>
        </div>
        
        <!-- 统计概览 -->
        <h2>📊 数据概览</h2>
        <div class="summary-box">
            <div class="card">
                <h4>门店数</h4>
                <div class="value">{total_stores}</div>
            </div>
            <div class="card green">
                <h4>总订单数</h4>
                <div class="value">{total_orders:,}</div>
            </div>
            <div class="card orange">
                <h4>团购订单数</h4>
                <div class="value">{total_gb:,}</div>
            </div>
            <div class="card blue">
                <h4>总营收</h4>
                <div class="value">{total_rev:,.0f}</div>
            </div>
            <div class="card">
                <h4>团购营收</h4>
                <div class="value">{total_gb_rev:,.0f}</div>
            </div>
            <div class="card green">
                <h4>团购占比</h4>
                <div class="value">{gb_ratio:.1f}%</div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin:15px 0;font-size:14px">
            <div style="background:#e8f5e9;padding:12px;border-radius:5px;border-left:4px solid #4caf50">
                <strong>团购店: {len(gb_stores)}</strong><br>
                {', '.join(gb_stores['门店'].tolist()[:5])}{'...' if len(gb_stores) > 5 else ''}
            </div>
            <div style="background:#fff3e0;padding:12px;border-radius:5px;border-left:4px solid #ff9800">
                <strong>混合型: {len(mix_stores)}</strong><br>
                {', '.join(mix_stores['门店'].tolist()[:5])}{'...' if len(mix_stores) > 5 else ''}
            </div>
            <div style="background:#e3f2fd;padding:12px;border-radius:5px;border-left:4px solid #2196f3">
                <strong>消费型: {len(consume_stores)}</strong><br>
                {', '.join(consume_stores['门店'].tolist()[:5])}{'...' if len(consume_stores) > 5 else ''}
            </div>
        </div>
    '''

    # 总体汇总表
    html += '''
        <h2>📈 门店汇总表</h2>
        <table>
            <tr>
                <th>#</th>
                <th>门店</th>
                <th>门店类型</th>
                <th>总订单</th>
                <th>团购订单</th>
                <th>团购占比</th>
                <th>总营收</th>
                <th>团购营收</th>
            </tr>
    '''
    for i, (idx, row) in enumerate(summary.iterrows(), 1):
        type_color = {
            '团购店': '#4caf50',
            '混合型': '#ff9800',
            '消费型': '#2196f3'
        }
        html += f'''
            <tr>
                <td>{i}</td>
                <td><strong>{row['门店']}</strong></td>
                <td style="color:{type_color.get(row['门店类型'], '#333')};font-weight:bold">{row['门店类型']}</td>
                <td>{row['总订单']:,}</td>
                <td>{row['团购订单']:,}</td>
                <td class="pos">{row['团购占比']:.1f}%</td>
                <td class="pos">{row['总营收']:,.0f}</td>
                <td class="pos">{row['团购营收']:,.0f}</td>
            </tr>
        '''

    html += '''</table>'''

    # 时段统计
    if not period.empty:
        html += '''
            <h2>⏰ 时段统计</h2>
            <table>
                <tr>
                    <th>门店</th>
                    <th>时段</th>
                    <th>总订单</th>
                    <th>团购订单</th>
                    <th>团购占比</th>
                </tr>
        '''
        for _, row in period.iterrows():
            html += f'''
                <tr>
                    <td>{row['门店']}</td>
                    <td>{row['time_period']}</td>
                    <td>{row['总订单']}</td>
                    <td>{row['团购订单']}</td>
                    <td class="pos">{row['团购占比']:.1f}%</td>
                </tr>
            '''
        html += '''</table>'''

    # 套餐明细
    if not pkgs.empty:
        html += '''
            <h2>🎁 套餐明细</h2>
        '''
        
        for store in sorted(pkgs['门店'].unique()):
            store_pkgs = pkgs[pkgs['门店'] == store]
            # 按销售金额排序，只取TOP10
            store_pkgs = store_pkgs.sort_values('销售金额', ascending=False).head(10)
            
            html += f'<h3>🏪 {store} (TOP10)</h3><table>'
            html += '''
                <tr>
                    <th>#</th>
                    <th>套餐名称</th>
                    <th>销售数量</th>
                    <th>销售金额</th>
                    <th>应收金额</th>
                    <th>单价</th>
                    <th>包含商品</th>
                </tr>
            '''
            for i, (idx, row) in enumerate(store_pkgs.iterrows(), 1):
                html += f'''
                    <tr>
                        <td>{i}</td>
                        <td><strong>{row['package']}</strong></td>
                        <td>{row['销售数量']}</td>
                        <td class="pos">{row['销售金额']:,.2f}</td>
                        <td>{row['应收金额']:,.2f}</td>
                        <td class="pos">{row['单价']:.2f}</td>
                        <td style="max-width:300px;font-size:11px">{row['包含商品'] or ''}</td>
                    </tr>
                '''
            html += '</table>'

    html += f'''
        <div class="footer">
            糖果华庭 KTV - 团购月度分析报告<br>
            {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
</body>
</html>'''

    # 保存HTML
    html_file = OUTPUT_DIR / f'团购月度分析报告_v2_{start_date}_{end_date}.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ HTML: {html_file}')

    # 保存PDF
    pdf_dir = PROJECT_ROOT / 'data' / 'output_pdf'
    pdf_dir.mkdir(exist_ok=True)
    pdf_file = pdf_dir / f'团购月度分析报告_v2_{start_date}_{end_date}.pdf'
    
    for cp in [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium'
    ]:
        if Path(cp).exists():
            break
    else:
        print('⚠️ 未找到Chrome，跳过PDF')
        return html_file

    import subprocess
    result = subprocess.run([
        cp, '--headless=new', '--disable-gpu', '--no-sandbox',
        f'--print-to-pdf={pdf_file.absolute()}', '--no-margins',
        str(html_file.absolute())
    ], capture_output=True, text=True)
    
    if result.returncode == 0 and pdf_file.exists() and pdf_file.stat().st_size > 1000:
        print(f'✅ PDF: {pdf_file}')
    
    return html_file


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, help='开始日期')
    parser.add_argument('--end', type=str, help='结束日期')
    parser.add_argument('--days', type=int, default=30, help='天数')
    args = parser.parse_args()
    
    generate_monthly_report(args.start, args.end, args.days)
