#!/usr/bin/env python3
"""
团购同比分析报告
对比去年5月与今年5月的团购数据
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.database import query

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")
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


def load_last_year_data():
    """加载去年5月的团购数据（从Excel文件）"""
    print("⏳ 加载去年(2025年5月)数据...")
    
    store_data = {}
    
    for store in ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']:
        store_data[store] = {'美团': None, '抖音': None}
        
        for platform in ['美团', '抖音']:
            file_path = GROUP_BUY_DIR / f"{store}{platform}.xlsx"
            if not file_path.exists():
                continue
                
            try:
                df = pd.read_excel(file_path)
                
                if platform == '美团':
                    if '消费时间' in df.columns:
                        df['data_date'] = pd.to_datetime(df['消费时间']).dt.date
                        df = df[(df['data_date'] >= date(2025, 5, 1)) & (df['data_date'] <= date(2025, 5, 31))]
                    store_data[store]['美团'] = df
                else:
                    if '下单时间' in df.columns:
                        df['data_date'] = pd.to_datetime(df['下单时间']).dt.date
                        df = df[(df['data_date'] >= date(2025, 5, 1)) & (df['data_date'] <= date(2025, 5, 31))]
                    store_data[store]['抖音'] = df
            except Exception as e:
                print(f"   ⚠️ {store}{platform} 读取失败: {e}")
    
    return store_data


def load_this_year_data():
    """加载今年5月的团购数据（从数据库）"""
    print("⏳ 加载今年(2026年5月)数据...")
    
    sm = store_map()
    
    od = query("""
        SELECT store_id, data_date, order_no, open_time, source_channel,
               actual_amount, should_amount, order_type, room_no
        FROM order_detail
        WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-31'
          AND order_type IN ('开房单', '点单')
    """)
    
    psd = query("""
        SELECT store_id, data_date, room_no, package, product_name
        FROM product_sales_detail
        WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-31'
          AND order_type IN ('开房单', '点单', '开房套餐')
          AND (package LIKE '%%团购%%' OR package LIKE '%%套餐%%')
    """)
    
    if od.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    od['门店'] = od['store_id'].map(sm).apply(unify)
    od = od[od['门店'].notna()]
    od['is_groupbuy'] = od['source_channel'].isin(GB_SOURCES).astype(int)
    
    if not psd.empty:
        psd['门店'] = psd['store_id'].map(sm).apply(unify)
        psd = psd[psd['门店'].notna()]
    
    return od, psd


def analyze_last_year(store_data):
    """分析去年数据"""
    results = {}
    
    for store in store_data:
        results[store] = {
            '美团订单': 0, '美团营收': 0,
            '抖音订单': 0, '抖音营收': 0,
            '总订单': 0, '总营收': 0,
            '热门套餐': []
        }
        
        meituan = store_data[store]['美团']
        douyin = store_data[store]['抖音']
        
        def clean_amount(s):
            if pd.isna(s):
                return 0.0
            s = str(s).strip()
            s = s.replace('¥', '').replace('元', '').replace(',', '')
            try:
                return float(s)
            except:
                return 0.0
        
        if meituan is not None and not meituan.empty:
            results[store]['美团订单'] = len(meituan)
            if '消费金额' in meituan.columns:
                results[store]['美团营收'] = float(meituan['消费金额'].apply(clean_amount).sum())
            elif '实际支付' in meituan.columns:
                results[store]['美团营收'] = float(meituan['实际支付'].apply(clean_amount).sum())
            else:
                results[store]['美团营收'] = 0.0
            
            if '商品信息' in meituan.columns:
                pkg_counts = meituan['商品信息'].value_counts().head(5)
                results[store]['热门套餐'].extend([f"{k}: {v}单" for k, v in pkg_counts.items()])
        
        if douyin is not None and not douyin.empty:
            results[store]['抖音订单'] = len(douyin)
            if '券用户实付金额' in douyin.columns:
                results[store]['抖音营收'] = float(douyin['券用户实付金额'].apply(clean_amount).sum())
            elif '用户实付金额' in douyin.columns:
                results[store]['抖音营收'] = float(douyin['用户实付金额'].apply(clean_amount).sum())
            else:
                results[store]['抖音营收'] = 0.0
            
            if '商品名称' in douyin.columns:
                pkg_counts = douyin['商品名称'].value_counts().head(5)
                results[store]['热门套餐'].extend([f"{k}: {v}单" for k, v in pkg_counts.items()])
        
        results[store]['总订单'] = results[store]['美团订单'] + results[store]['抖音订单']
        results[store]['总营收'] = float(results[store]['美团营收']) + float(results[store]['抖音营收'])
    
    return results


def analyze_this_year(od_df, psd):
    """分析今年数据"""
    results = {}
    
    summary = od_df.groupby('门店').agg(
        总订单=('order_no', 'nunique'),
        团购订单=('is_groupbuy', 'sum'),
        总营收=('actual_amount', 'sum'),
        团购营收=('actual_amount', lambda x: x[od_df.loc[x.index, 'is_groupbuy'] == 1].sum())
    ).reset_index()
    
    gb_orders = od_df[od_df['is_groupbuy'] == 1].copy()
    gb_orders['平台'] = gb_orders['source_channel'].apply(lambda x: '抖音' if x == '抖音' else ('美团' if x == '美团大众' else '其他'))
    
    platform_summary = gb_orders.groupby(['门店', '平台']).agg(
        订单数=('order_no', 'nunique'),
        营收=('actual_amount', 'sum')
    ).reset_index()
    
    pkg_list = []
    if not psd.empty and not gb_orders.empty:
        pkg_map = {}
        for (store, room_no), group in psd.groupby(['门店', 'room_no']):
            pkg_names = group['package'].dropna().unique()
            if pkg_names.size > 0:
                pkg_name = next((p for p in pkg_names if p), '未知套餐')
                pkg_map[(store, room_no)] = pkg_name
        
        for _, order in gb_orders.iterrows():
            store = order['门店']
            room_no = order['room_no'] if pd.notna(order['room_no']) else ''
            if (store, room_no) in pkg_map:
                pkg_list.append({'门店': store, 'package': pkg_map[(store, room_no)]})
            else:
                pkg_list.append({'门店': store, 'package': f"{order['source_channel']}团购"})
    
    for _, row in summary.iterrows():
        store = row['门店']
        results[store] = {
            '总订单': row['总订单'],
            '总营收': row['总营收'],
            '团购订单': row['团购订单'],
            '团购营收': row['团购营收'],
            '美团订单': 0, '美团营收': 0,
            '抖音订单': 0, '抖音营收': 0,
            '热门套餐': []
        }
        
        ps = platform_summary[platform_summary['门店'] == store]
        for _, p in ps.iterrows():
            if p['平台'] == '美团':
                results[store]['美团订单'] = p['订单数']
                results[store]['美团营收'] = p['营收']
            elif p['平台'] == '抖音':
                results[store]['抖音订单'] = p['订单数']
                results[store]['抖音营收'] = p['营收']
        
        if pkg_list:
            store_pkgs = [p for p in pkg_list if p['门店'] == store]
            if store_pkgs:
                pkg_df = pd.DataFrame(store_pkgs)
                top_pkgs = pkg_df['package'].value_counts().head(5)
                results[store]['热门套餐'] = [f"{k}: {v}单" for k, v in top_pkgs.items()]
    
    return results


def generate_comparison_report(last_year_data, this_year_data):
    """生成同比报告"""
    print("📊 生成同比分析报告...")
    
    stores = set(list(last_year_data.keys()) + list(this_year_data.keys()))
    stores = sorted([s for s in stores if s])
    
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>团购同比分析报告 - 2025年5月vs2026年5月</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#333;background:#f5f5f5;line-height:1.6}}
.c{{max-width:1800px;margin:0 auto;background:#fff;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:25px;font-size:26px}}
h2{{color:#34495e;margin:35px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:19px}}
h3{{color:#4a6fa5;margin:20px 0 8px;font-size:15px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:12px}}
th,td{{border:1px solid #ddd;padding:8px 10px;text-align:left}}
th{{background:#f0f8ff;font-weight:600;white-space:nowrap}}
tr:nth-child(even){{background:#f9f9f9}}
tr:hover{{background:#f0f0f0}}
.pos{{color:#28a745;font-weight:bold}}
.neg{{color:#e74c3c;font-weight:bold}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:18px 0}}
.card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px;border-radius:8px;text-align:center}}
.card.g{{background:linear-gradient(135deg,#11998e,#38ef7d)}}
.card.o{{background:linear-gradient(135deg,#f093fb,#f5576c)}}
.card.b{{background:linear-gradient(135deg,#4facfe,#00f2fe)}}
.card.r{{background:linear-gradient(135deg,#e74c3c,#c0392b)}}
.card h3{{color:#fff;margin:0;font-size:12px;opacity:.9}}
.card .v{{font-size:24px;font-weight:bold;margin:6px 0}}
.sec{{margin-bottom:30px;padding-bottom:15px;border-bottom:2px solid #eee}}
.sec:last-child{{border-bottom:none;margin-bottom:0}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin:15px 0;font-size:13px}}
.summary-box{{background:#f8f9fa;padding:12px 15px;border-radius:6px;border-left:4px solid #3498db}}
.footer{{text-align:center;color:#999;font-size:12px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}}
</style></head><body><div class="c">
<h1>📈 团购同比分析报告</h1>
<div style="color:#7f8c8d;margin-bottom:20px;font-size:13px;">
对比周期：<b>2025年5月</b> vs <b>2026年5月</b><br>
数据来源：2025年来自Excel文件，2026年来自order_detail数据库
</div>
"""
    
    ly_total_orders = sum([last_year_data[s]['总订单'] for s in last_year_data if s in last_year_data])
    ly_total_rev = sum([last_year_data[s]['总营收'] for s in last_year_data if s in last_year_data])
    ly_meituan_orders = sum([last_year_data[s]['美团订单'] for s in last_year_data if s in last_year_data])
    ly_meituan_rev = sum([last_year_data[s]['美团营收'] for s in last_year_data if s in last_year_data])
    ly_douyin_orders = sum([last_year_data[s]['抖音订单'] for s in last_year_data if s in last_year_data])
    ly_douyin_rev = sum([last_year_data[s]['抖音营收'] for s in last_year_data if s in last_year_data])
    
    ty_total_orders = sum([this_year_data[s]['总订单'] for s in this_year_data if s in this_year_data])
    ty_total_rev = sum([this_year_data[s]['总营收'] for s in this_year_data if s in this_year_data])
    ty_gb_orders = sum([this_year_data[s]['团购订单'] for s in this_year_data if s in this_year_data])
    ty_gb_rev = sum([this_year_data[s]['团购营收'] for s in this_year_data if s in this_year_data])
    ty_meituan_orders = sum([this_year_data[s]['美团订单'] for s in this_year_data if s in this_year_data])
    ty_meituan_rev = sum([this_year_data[s]['美团营收'] for s in this_year_data if s in this_year_data])
    ty_douyin_orders = sum([this_year_data[s]['抖音订单'] for s in this_year_data if s in this_year_data])
    ty_douyin_rev = sum([this_year_data[s]['抖音营收'] for s in this_year_data if s in this_year_data])
    
    def pct(a, b):
        if b == 0:
            return '-'
        v = (a - b) / b * 100
        return f"{v:+.1f}%"
    
    html += '<div class="cards">'
    html += f'<div class="card"><h3>门店数量</h3><div class="v">{len(stores)}</div></div>'
    html += f'<div class="card.g"><h3>总订单数(2025)</h3><div class="v">{ly_total_orders:,.0f}</div></div>'
    html += f'<div class="card.g"><h3>总订单数(2026)</h3><div class="v">{ty_total_orders:,.0f}</div></div>'
    chg = (ty_total_orders - ly_total_orders) / ly_total_orders * 100 if ly_total_orders > 0 else 0
    cls = 'pos' if chg >= 0 else 'neg'
    html += f'<div class="card.o"><h3>订单变化</h3><div class="v"><span class="{cls}">{pct(ty_total_orders, ly_total_orders)}</span></div></div>'
    html += '</div>'
    
    html += '<div class="cards">'
    html += f'<div class="card.g"><h3>总营收(2025)</h3><div class="v">{ly_total_rev:,.0f}</div></div>'
    html += f'<div class="card.g"><h3>总营收(2026)</h3><div class="v">{ty_total_rev:,.0f}</div></div>'
    chg = (ty_total_rev - ly_total_rev) / ly_total_rev * 100 if ly_total_rev > 0 else 0
    cls = 'pos' if chg >= 0 else 'neg'
    html += f'<div class="card.o"><h3>营收变化</h3><div class="v"><span class="{cls}">{pct(ty_total_rev, ly_total_rev)}</span></div></div>'
    html += '</div>'
    
    html += '<div class="sec"><h2>一、平台对比分析</h2><table>'
    html += '<tr><th>指标</th><th>2025年5月</th><th>2026年5月</th><th>变化幅度</th></tr>'
    
    html += f'<tr><td><b>美团订单</b></td><td>{ly_meituan_orders:,.0f}</td><td>{ty_meituan_orders:,.0f}</td>'
    cls = 'pos' if ty_meituan_orders >= ly_meituan_orders else 'neg'
    html += f'<td><span class="{cls}">{pct(ty_meituan_orders, ly_meituan_orders)}</span></td></tr>'
    
    html += f'<tr><td><b>美团营收</b></td><td>{ly_meituan_rev:,.0f}</td><td>{ty_meituan_rev:,.0f}</td>'
    cls = 'pos' if ty_meituan_rev >= ly_meituan_rev else 'neg'
    html += f'<td><span class="{cls}">{pct(ty_meituan_rev, ly_meituan_rev)}</span></td></tr>'
    
    html += f'<tr><td><b>抖音订单</b></td><td>{ly_douyin_orders:,.0f}</td><td>{ty_douyin_orders:,.0f}</td>'
    cls = 'pos' if ty_douyin_orders >= ly_douyin_orders else 'neg'
    html += f'<td><span class="{cls}">{pct(ty_douyin_orders, ly_douyin_orders)}</span></td></tr>'
    
    html += f'<tr><td><b>抖音营收</b></td><td>{ly_douyin_rev:,.0f}</td><td>{ty_douyin_rev:,.0f}</td>'
    cls = 'pos' if ty_douyin_rev >= ly_douyin_rev else 'neg'
    html += f'<td><span class="{cls}">{pct(ty_douyin_rev, ly_douyin_rev)}</span></td></tr>'
    
    html += '</table></div>'
    
    html += '<div class="sec"><h2>二、各门店同比详细分析</h2><table>'
    html += '<tr><th>门店</th><th colspan="4">2025年5月</th><th colspan="4">2026年5月</th><th colspan="2">同比变化</th></tr>'
    html += '<tr><th></th><th>总订单</th><th>美团</th><th>抖音</th><th>总营收</th><th>总订单</th><th>美团</th><th>抖音</th><th>团购营收</th><th>订单变化</th><th>营收变化</th></tr>'
    
    for store in stores:
        ly = last_year_data.get(store, {'总订单': 0, '美团订单': 0, '抖音订单': 0, '总营收': 0})
        ty = this_year_data.get(store, {'总订单': 0, '美团订单': 0, '抖音订单': 0, '团购营收': 0})
        
        ord_chg = (ty['总订单'] - ly['总订单']) / ly['总订单'] * 100 if ly['总订单'] > 0 else 0
        rev_chg = (ty['团购营收'] - ly['总营收']) / ly['总营收'] * 100 if ly['总营收'] > 0 else 0
        
        ord_cls = 'pos' if ord_chg >= 0 else 'neg'
        rev_cls = 'pos' if rev_chg >= 0 else 'neg'
        
        html += f"<tr><td><b>{store}</b></td>"
        html += f"<td>{ly['总订单']:,.0f}</td><td>{ly['美团订单']:,.0f}</td><td>{ly['抖音订单']:,.0f}</td><td>{ly['总营收']:,.0f}</td>"
        html += f"<td>{ty['总订单']:,.0f}</td><td>{ty['美团订单']:,.0f}</td><td>{ty['抖音订单']:,.0f}</td><td>{ty['团购营收']:,.0f}</td>"
        html += f"<td><span class=\"{ord_cls}\">{pct(ty['总订单'], ly['总订单'])}</span></td>"
        html += f"<td><span class=\"{rev_cls}\">{pct(ty['团购营收'], ly['总营收'])}</span></td>"
        html += "</tr>"
    
    html += '</table></div>'
    
    html += '<div class="sec"><h2>三、热门套餐变化对比</h2>'
    
    for store in stores:
        ly_pkgs = last_year_data.get(store, {}).get('热门套餐', [])
        ty_pkgs = this_year_data.get(store, {}).get('热门套餐', [])
        
        if ly_pkgs or ty_pkgs:
            html += f'<h3>{store}</h3>'
            html += '<table><tr><th>2025年5月热门套餐</th><th>2026年5月热门套餐</th></tr>'
            max_len = max(len(ly_pkgs), len(ty_pkgs))
            for i in range(max_len):
                ly_p = ly_pkgs[i] if i < len(ly_pkgs) else ''
                ty_p = ty_pkgs[i] if i < len(ty_pkgs) else ''
                html += f'<tr><td>{ly_p}</td><td>{ty_p}</td></tr>'
            html += '</table>'
    
    html += '</div>'
    
    html += '<div class="sec"><h2>四、关键发现总结</h2>'
    
    order_chg = (ty_total_orders - ly_total_orders) / ly_total_orders * 100 if ly_total_orders > 0 else 0
    rev_chg = (ty_total_rev - ly_total_rev) / ly_total_rev * 100 if ly_total_rev > 0 else 0
    meituan_chg = (ty_meituan_orders - ly_meituan_orders) / ly_meituan_orders * 100 if ly_meituan_orders > 0 else 0
    douyin_chg = (ty_douyin_orders - ly_douyin_orders) / ly_douyin_orders * 100 if ly_douyin_orders > 0 else 0
    
    html += '<ul style="margin-left:20px;line-height:2.2;font-size:14px">'
    if order_chg > 0:
        html += f'<li>✅ <b>总订单增长</b>：同比{order_chg:.1f}%，业务整体向好</li>'
    else:
        html += f'<li>⚠️ <b>总订单下滑</b>：同比{order_chg:.1f}%，需要关注</li>'
    
    if rev_chg > 0:
        html += f'<li>💰 <b>总营收增长</b>：同比{rev_chg:.1f}%，营收表现良好</li>'
    else:
        html += f'<li>⚠️ <b>总营收下滑</b>：同比{rev_chg:.1f}%，需要分析原因</li>'
    
    if meituan_chg > 0:
        html += f'<li>🍜 <b>美团增长</b>：订单同比{meituan_chg:.1f}%，美团渠道表现强劲</li>'
    else:
        html += f'<li>⚠️ <b>美团下滑</b>：订单同比{meituan_chg:.1f}%，需要优化美团策略</li>'
    
    if douyin_chg > 0:
        html += f'<li>🎵 <b>抖音增长</b>：订单同比{douyin_chg:.1f}%，抖音渠道持续发力</li>'
    else:
        html += f'<li>⚠️ <b>抖音下滑</b>：订单同比{douyin_chg:.1f}%，需要调整抖音投放</li>'
    
    html += '</ul></div>'
    
    html += f"""<div class="footer">
团购同比分析报告 | 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} |
对比周期：2025年5月vs2026年5月 | 数据来源：Excel+数据库 | 糖果华庭 KTV
</div></div></body></html>"""
    
    output_path = OUTPUT_DIR / "团购同比分析报告_2025vs2026.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML报告: {output_path}")
    
    import subprocess
    import os
    def clear_extended_attributes(fp):
        try:
            subprocess.run(['xattr', '-c', str(fp)], capture_output=True, check=True)
            os.chmod(str(fp), 0o644)
        except Exception:
            pass
    clear_extended_attributes(output_path)
    
    pdf_dir = PROJECT_ROOT / "data" / "output_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "团购同比分析报告_2025vs2026.pdf"
    
    for cp in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium"]:
        if Path(cp).exists():
            break
    else:
        print("   ⚠️ 未找到Chrome，跳过PDF")
        return output_path
    
    r = subprocess.run([cp, "--headless=new", "--disable-gpu", "--no-sandbox",
                        f"--print-to-pdf={pdf_path.absolute()}", "--no-margins",
                        str(output_path.absolute())], capture_output=True, text=True)
    
    if r.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
        print(f"   ✅ PDF报告: {pdf_path}")
        clear_extended_attributes(pdf_path)
    
    return output_path


def main():
    print("=" * 80)
    print("团购同比分析 - 2025年5月 vs 2026年5月")
    print("=" * 80)
    print()
    
    last_year_data = load_last_year_data()
    last_year_data = analyze_last_year(last_year_data)
    this_year_od, this_year_psd = load_this_year_data()
    this_year_data = analyze_this_year(this_year_od, this_year_psd)
    
    print()
    print("📊 数据加载完成")
    print(f"   - 去年有数据门店: {len([s for s in last_year_data if last_year_data[s]['总订单'] > 0])}")
    print(f"   - 今年有数据门店: {len([s for s in this_year_data if this_year_data[s]['总订单'] > 0])}")
    print()
    
    report_path = generate_comparison_report(last_year_data, this_year_data)
    
    print()
    print("🎉 同比分析完成！")


if __name__ == "__main__":
    main()
