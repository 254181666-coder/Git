#!/usr/bin/env python3
"""
团购月度分析报告生成脚本
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

    if od.empty:
        return pd.DataFrame(), pd.DataFrame()

    od['门店'] = od['store_id'].map(sm).apply(unify)
    od = od[od['门店'].notna()]
    od['is_groupbuy'] = od['source_channel'].isin(GB_SOURCES).astype(int)
    od['time_period'] = od['open_time'].apply(to_period)

    if not psd.empty:
        psd['门店'] = psd['store_id'].map(sm).apply(unify)
        psd = psd[psd['门店'].notna()]

    return od, psd


def build_daily_stats(od_df):
    return od_df.groupby(['data_date', '门店']).agg(
        总订单=('order_no', 'nunique'),
        团购订单=('is_groupbuy', 'sum'),
        总营收=('actual_amount', 'sum'),
        团购营收=('actual_amount', lambda x: x[od_df.loc[x.index, 'is_groupbuy'] == 1].sum())
    ).reset_index()


def build_monthly_summary(od_df):
    summary = od_df.groupby('门店').agg(
        总订单=('order_no', 'nunique'),
        团购订单=('is_groupbuy', 'sum'),
        营业天数=('data_date', 'nunique'),
        总营收=('actual_amount', 'sum'),
        团购营收=('actual_amount', lambda x: x[od_df.loc[x.index, 'is_groupbuy'] == 1].sum())
    ).reset_index()
    summary['团购占比'] = (summary['团购订单'] / summary['总订单'] * 100).round(1)
    summary['日均订单'] = (summary['总订单'] / summary['营业天数']).round(0).astype(int)
    summary['日均团购'] = (summary['团购订单'] / summary['营业天数']).round(0).astype(int)

    def classify(r):
        if r['团购占比'] >= 70:
            return '团购店'
        if r['团购占比'] >= 30:
            return '混合型'
        return '消费型'

    summary['门店类型'] = summary.apply(classify, axis=1)
    return summary.sort_values('团购占比', ascending=False)


def build_period_stats(od_df):
    period = od_df.groupby(['门店', 'time_period']).agg(
        总订单=('order_no', 'nunique'),
        团购订单=('is_groupbuy', 'sum'),
        总营收=('actual_amount', 'sum'),
        团购营收=('actual_amount', lambda x: x[od_df.loc[x.index, 'is_groupbuy'] == 1].sum())
    ).reset_index()
    period['团购占比'] = (period['团购订单'] / period['总订单'] * 100).round(1)
    return period


def build_package_stats(od_df, psd):
    gb_orders = od_df[od_df['is_groupbuy'] == 1].copy()
    
    if gb_orders.empty:
        return pd.DataFrame()

    pkg_list = []
    pkg_product_quantities = {}
    
    if not psd.empty:
        # 先建立订单到套餐的准确映射：(data_date, store_id, room_no) -> {pkg_name: ...}
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
                            # 从套餐名称中尝试提取价格数字
                            import re
                            numbers = re.findall(r'\d+\.?\d*', candidate_pkg)
                            for num_str in numbers:
                                try:
                                    pkg_price = float(num_str)
                                    diff = abs(pkg_price - should_amount)
                                    # 只匹配价格差异在10元以内的，防止误匹配
                                    if diff < 10 and diff < best_diff:
                                        best_diff = diff
                                        best_match_pkg = candidate_pkg
                                except ValueError:
                                    continue
                        
                        if best_match_pkg:
                            pkg_name = best_match_pkg
                        else:
                            # 没有匹配上，取第一个
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
    
    # 进一步过滤：确保套餐名称中的价格和应收金额匹配
    import re
    
    def filter_pkg_order(row):
        pkg_name = row['package']
        should_amount = row['应收金额']
        
        # 从套餐名称中提取所有可能的价格数字
        numbers = re.findall(r'\d+\.?\d*', pkg_name)
        
        if not numbers:
            # 没有数字，通过
            return True
        
        # 检查是否有任何价格和应收金额匹配（10元容差）
        for num_str in numbers:
            try:
                pkg_price = float(num_str)
                if abs(pkg_price - should_amount) < 10:
                    return True
            except ValueError:
                continue
        
        # 检查是否是"团购"类的，如果是，通过
        if '团购' in pkg_name and len(numbers) == 0:
            return True
        
        # 检查是否是"开机套"类的
        if '开机' in pkg_name:
            return True
        
        # 没有匹配，跳过这个订单
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

    od_df, psd = load_monthly_data(str(start_date), str(end_date))
    if od_df.empty:
        print(f"❌ {start_date} ~ {end_date} 无数据")
        return None

    daily = build_daily_stats(od_df)
    summary = build_monthly_summary(od_df)
    period = build_period_stats(od_df)
    pkgs = build_package_stats(od_df, psd)

    stores_list = summary['门店'].tolist()
    all_dates = sorted(daily['data_date'].unique())

    total_stores = summary['门店'].nunique()
    total_orders = summary['总订单'].sum()
    total_gb = summary['团购订单'].sum()
    total_rev = summary['总营收'].sum()
    total_gb_rev = summary['团购营收'].sum()
    gb_ratio = (total_gb / total_orders * 100) if total_orders > 0 else 0

    gb_stores = summary[summary['门店类型'] == '团购店']
    mix_stores = summary[summary['门店类型'] == '混合型']
    consume_stores = summary[summary['门店类型'] == '消费型']

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>团购月度分析报告</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#333;background:#f5f5f5;line-height:1.6}}
.c{{max-width:1600px;margin:0 auto;background:#fff;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:25px;font-size:26px}}
h2{{color:#34495e;margin:35px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:19px}}
h3{{color:#4a6fa5;margin:20px 0 8px;font-size:15px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:12px}}
th,td{{border:1px solid #ddd;padding:6px 8px;text-align:left}}
th{{background:#f0f8ff;font-weight:600;white-space:nowrap}}
tr:nth-child(even){{background:#f9f9f9}}
tr:hover{{background:#f0f0f0}}
.pos{{color:#28a745;font-weight:bold}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:18px 0}}
.card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px;border-radius:8px;text-align:center}}
.card.g{{background:linear-gradient(135deg,#11998e,#38ef7d)}}
.card.o{{background:linear-gradient(135deg,#f093fb,#f5576c)}}
.card.b{{background:linear-gradient(135deg,#4facfe,#00f2fe)}}
.card.r{{background:linear-gradient(135deg,#e74c3c,#c0392b)}}
.card h3{{color:#fff;margin:0;font-size:12px;opacity:.9}}
.card .v{{font-size:24px;font-weight:bold;margin:6px 0}}
.sec{{margin-bottom:30px;padding-bottom:15px;border-bottom:2px solid #eee}}
.sec:last-child{{border-bottom:none;margin-bottom:0}}
.tag-g{{background:#e74c3c;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px}}
.tag-m{{background:#f39c12;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px}}
.tag-c{{background:#27ae60;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px}}
.trend-row{{display:flex;flex-wrap:wrap;gap:20px;justify-content:center}}
.trend-card{{background:#fff;border:1px solid #eee;border-radius:8px;padding:15px;min-width:320px;flex:1;max-width:520px}}
.trend-card h4{{font-size:13px;color:#555;margin-bottom:8px}}
.footer{{text-align:center;color:#999;font-size:12px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin:15px 0;font-size:13px}}
.summary-box{{background:#f8f9fa;padding:12px 15px;border-radius:6px;border-left:4px solid #3498db}}
</style></head><body><div class="c">
<h1>📊 团购月度分析报告</h1>
<div style="color:#7f8c8d;margin-bottom:20px;font-size:13px;">
分析周期：<b>{start_date}</b> ~ <b>{end_date}</b>（共 {(end_date - start_date).days + 1} 天）<br>
团购判定：source_channel ∈ {{抖音, 美团大众, 线下团购}} | 时段：日场(9-18)/晚场(18-24)/午夜(0-9)
</div>

<div class="cards">
  <div class="card"><h3>统计门店</h3><div class="v">{total_stores}</div></div>
  <div class="card.g"><h3>总订单数</h3><div class="v">{total_orders:,.0f}</div></div>
  <div class="card.o"><h3>团购订单数</h3><div class="v">{total_gb:,.0f}</div></div>
  <div class="card.b"><h3>整体团购占比</h3><div class="v">{gb_ratio:.1f}%</div></div>
  <div class="card.r"><h3>团购店数量</h3><div class="v">{len(gb_stores)}</div></div>
  <div class="card"><h3>混合型</h3><div class="v">{len(mix_stores)}</div></div>
</div>
<div class="cards">
  <div class="card.g"><h3>月总营收</h3><div class="v">{total_rev:,.0f}</div></div>
  <div class="card.o"><h3>团购营收</h3><div class="v">{total_gb_rev:,.0f}</div></div>
</div>
"""

    html += '<div class="sec"><h2>一、各门店月度总览</h2><table>'
    html += '<tr><th>门店</th><th>类型</th><th>总订单</th><th>团购订单</th><th>团购占比</th><th>日均订单</th><th>日均团购</th><th>总营收</th><th>团购营收</th><th>营业天数</th></tr>'
    for _, r in summary.iterrows():
        tag = 'tag-g' if r['门店类型'] == '团购店' else ('tag-m' if r['门店类型'] == '混合型' else 'tag-c')
        html += f"<tr><td><b>{r['门店']}</b></td><td><span class='{tag}'>{r['门店类型']}</span></td><td>{r['总订单']:,.0f}</td><td class='pos'>{r['团购订单']:,.0f}</td><td>{r['团购占比']}%</td><td>{r['日均订单']}</td><td class='pos'>{r['日均团购']}</td><td>{r['总营收']:,.0f}</td><td class='pos'>{r['团购营收']:,.0f}</td><td>{r['营业天数']}</td></tr>"
    html += '</table></div>'

    html += '<div class="sec"><h2>二、各门店每日团购占比趋势</h2><div class="trend-row">'
    for store in stores_list:
        sd = daily[daily['门店'] == store].sort_values('data_date')
        if len(sd) < 3:
            continue
        ratios = (sd['团购订单'] / sd['总订单'] * 100).tolist()
        dates = sd['data_date'].tolist()

        stype = summary[summary['门店'] == store]
        col = '#e74c3c' if not stype.empty and stype.iloc[0]['门店类型'] == '团购店' else \
              '#f39c12' if not stype.empty and stype.iloc[0]['门店类型'] == '混合型' else '#27ae60'

        chart = svg_trend_line(ratios, dates, width=450, height=110, color=col)
        avg_r = np.mean(ratios)
        html += f'<div class="trend-card"><h4>{store} — 月均 {avg_r:.1f}%</h4>{chart}</div>'
    html += '</div></div>'

    html += '<div class="sec"><h2>三、月度各时段团购分析</h2>'
    periods_order = ['日场', '晚场', '午夜场']

    for period_name in periods_order:
        pp = period[period['time_period'] == period_name].sort_values('团购占比', ascending=False)
        if pp.empty:
            continue
        html += f'<h3>{period_name}</h3><table>'
        html += '<tr><th>门店</th><th>总订单</th><th>团购订单</th><th>团购占比</th><th>总营收</th><th>团购营收</th></tr>'
        for _, r in pp.iterrows():
            html += f"<tr><td><b>{r['门店']}</b></td><td>{r['总订单']:,.0f}</td><td class='pos'>{r['团购订单']:,.0f}</td><td>{r['团购占比']}%</td><td>{r['总营收']:,.0f}</td><td class='pos'>{r['团购营收']:,.0f}</td></tr>"
        html += '</table>'
    html += '</div>'

    html += '<div class="sec"><h2>四、月度热销团购套餐 Top 5</h2>'
    if not pkgs.empty:
        for store in stores_list:
            sp = pkgs[pkgs['门店'] == store].head(5)
            if sp.empty:
                continue
            html += f'<h3>{store}</h3><table>'
            html += '<tr><th>#</th><th>套餐名称</th><th>销售数量</th><th>销售金额</th><th>应收金额</th><th>单价(元)</th><th>包含商品</th></tr>'
            for i, (_, p) in enumerate(sp.iterrows(), 1):
                html += f"<tr><td>{i}</td><td><b>{p['package']}</b></td><td>{p['销售数量']:,.0f}</td><td class='pos'>{p['销售金额']:,.2f}</td><td>{p['应收金额']:,.2f}</td><td class='pos'>{p['单价']:.2f}</td><td>{p['包含商品']}</td></tr>"
            html += '</table>'
    else:
        html += '<p>暂无团购套餐数据</p>'
    html += '</div>'

    html += '<div class="sec"><h2>五、全店每日总量趋势</h2>'
    dd = daily.groupby('data_date').agg(总订单=('总订单', 'sum'), 团购订单=('团购订单', 'sum')).reset_index()
    dd['占比'] = (dd['团购订单'] / dd['总订单'] * 100).round(1)
    dd = dd.sort_values('data_date')

    daily_chart = svg_trend_line(dd['占比'].tolist(), dd['data_date'].tolist(), width=750, height=140, color='#8e44ad')
    html += f'<div style="text-align:center">{daily_chart}</div>'
    html += '<div style="text-align:center;color:#999;font-size:11px">每日整体团购占比趋势</div>'

    html += '<table style="margin-top:15px">'
    html += '<tr><th>日期</th><th>总订单</th><th>团购订单</th><th>团购占比</th></tr>'
    for _, r in dd.iterrows():
        html += f"<tr><td>{r['data_date']}</td><td>{r['总订单']:,.0f}</td><td class='pos'>{r['团购订单']:,.0f}</td><td>{r['占比']}%</td></tr>"
    html += '</table></div>'

    html += f"""<div class="sec"><h2>六、门店类型分布</h2>
<div class="summary-grid">
  <div class="summary-box" style="border-left-color:#e74c3c"><b>团购店</b><br><span style="font-size:22px">{len(gb_stores)}</span> 家</div>
  <div class="summary-box" style="border-left-color:#f39c12"><b>混合型</b><br><span style="font-size:22px">{len(mix_stores)}</span> 家</div>
  <div class="summary-box" style="border-left-color:#27ae60"><b>消费型</b><br><span style="font-size:22px">{len(consume_stores)}</span> 家</div>
</div>
<ul style="margin:15px 0 0 20px;line-height:2;">
<li><span class="tag-g">团购店</span>：团购占比 ≥ 70%，主要依赖平台引流</li>
<li><span class="tag-m">混合型</span>：30% ≤ 团购占比 &lt; 70%，团购与自然消费并存</li>
<li><span class="tag-c">消费型</span>：团购占比 &lt; 30%，以自然到店消费为主</li>
</ul></div>
"""

    html += f"""<div class="footer">
团购月度分析报告 | 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} |
周期 {start_date} ~ {end_date} | 数据来源：order_detail + product_sales_detail | 糖果华庭 KTV
</div></div></body></html>"""

    output_path = OUTPUT_DIR / f"团购月度报告_{start_date}_{end_date}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    clear_extended_attributes(output_path)
    print(f"✅ HTML: {output_path}")

    pdf_path = convert_html_to_pdf(output_path)
    if pdf_path:
        print(f"✅ PDF:  {pdf_path}")
    return output_path


def clear_extended_attributes(fp: Path):
    import subprocess
    import os
    try:
        subprocess.run(['xattr', '-c', str(fp)], capture_output=True, check=True)
        os.chmod(str(fp), 0o644)
    except Exception:
        pass


def convert_html_to_pdf(html_path: Path) -> Path:
    from src.config import PROJECT_ROOT
    pdf_dir = PROJECT_ROOT / "data" / "output_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / (html_path.stem + ".pdf")
    for cp in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium"]:
        if Path(cp).exists():
            break
    else:
        print("   ⚠️ 未找到Chrome，跳过PDF")
        return None
    import subprocess
    r = subprocess.run([cp, "--headless=new", "--disable-gpu", "--no-sandbox",
                        f"--print-to-pdf={pdf_path.absolute()}", "--no-margins",
                        str(html_path.absolute())], capture_output=True, text=True)
    if r.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
        print(f"   ✅ PDF ({pdf_path.stat().st_size/1024/1024:.1f} MB)")
        clear_extended_attributes(pdf_path)
        return pdf_path
    print(f"   ⚠️ PDF失败")
    return None


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="生成团购月度分析报告")
    p.add_argument("--start", help="起始日期 YYYY-MM-DD，默认30天前")
    p.add_argument("--end", help="结束日期 YYYY-MM-DD，默认昨天")
    p.add_argument("--days", type=int, default=30, help="天数，默认30天")
    a = p.parse_args()

    td = date.today()
    ed = a.end or (td - timedelta(days=1)).strftime("%Y-%m-%d")
    generate_monthly_report(start_date=a.start, end_date=ed, days=a.days)
