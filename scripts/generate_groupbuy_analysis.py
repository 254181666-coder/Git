#!/usr/bin/env python3
"""
团购分析报告生成脚本
分析各门店团购套餐销售情况，判断门店是团购店还是有消费的店面

核心逻辑：
1. order_detail 订单类型为开房单/点单 = 有效数据
2. order_detail.source_channel 含"抖音/美团/团购" = 团购订单
3. order_detail.open_time → 时段（日场9-18/晚场18-24/午夜0-9）
4. order_detail.actual_amount = 团购实际收入
5. product_sales_detail 通过 room_no 关联，获取套餐名称和包含商品
"""
import sys
from pathlib import Path
from datetime import datetime, date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.config import OUTPUT_DIR
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


def unify_name(n):
    if not n:
        return None
    n = str(n).strip()
    return STORE_NAME_MERGE.get(n, n)


def store_map():
    df = query("SELECT id, store_name FROM stores")
    return dict(zip(df['id'], df['store_name']))


def time_period(open_time):
    if pd.isna(open_time):
        return None
    h = open_time.hour
    if 9 <= h < 18:
        return '日场'
    elif 18 <= h < 24:
        return '晚场'
    else:
        return '午夜场'


def load_all_data(target_date):
    sm = store_map()

    od = query("""
        SELECT * FROM order_detail
        WHERE data_date = %s AND order_type IN ('开房单', '点单')
    """, (target_date,))
    if od.empty:
        return pd.DataFrame(), pd.DataFrame()

    od['store_name'] = od['store_id'].map(sm)
    od['门店'] = od['store_name'].apply(unify_name)
    od = od[od['门店'].notna()]
    od['time_period'] = od['open_time'].apply(time_period)
    od['is_groupbuy'] = od['source_channel'].isin(GB_SOURCES).astype(int)

    psd = query("""
        SELECT store_id, data_date, room_no, package, product_name
        FROM product_sales_detail
        WHERE data_date = %s AND order_type IN ('开房单', '点单', '开房套餐')
          AND (package LIKE '%%团购%%' OR package LIKE '%%套餐%%')
    """, (target_date,))

    gb_package_info = pd.DataFrame()
    if not psd.empty:
        psd['store_name'] = psd['store_id'].map(sm)
        psd['门店'] = psd['store_name'].apply(unify_name)
        gb_package_info = psd[psd['门店'].notna()].copy()

    return od, gb_package_info


def analyze_packages(od_df, gb_package_info):
    if od_df.empty:
        return {}

    gb_orders = od_df[od_df['is_groupbuy'] == 1].copy()
    if gb_orders.empty:
        return {}

    pkg_list = []

    if not gb_package_info.empty:
        pkg_map = {}
        for (store, room_no), group in gb_package_info.groupby(['门店', 'room_no']):
            pkg_names = group['package'].dropna().unique()
            products = ', '.join(set(group['product_name'].dropna()))
            if pkg_names.size > 0:
                pkg_name = next((p for p in pkg_names if p), '未知套餐')
                pkg_map[(store, room_no)] = (pkg_name, products)

        for _, order in gb_orders.iterrows():
            store = order['门店']
            room_no = order['room_no'] if pd.notna(order['room_no']) else ''
            actual_amount = order['actual_amount']
            should_amount = order['should_amount']

            if (store, room_no) in pkg_map:
                pkg_name, products = pkg_map[(store, room_no)]
            else:
                pkg_name = f"{order['source_channel']}团购"
                products = ''

            first_product = products.split(',')[0].strip() if products else ''
            pkg_list.append({
                '门店': store,
                'package': pkg_name,
                '销售数量': 1,
                '销售金额': actual_amount,
                '应收金额': should_amount,
                '包含商品': first_product
            })
    else:
        for _, order in gb_orders.iterrows():
            pkg_list.append({
                '门店': order['门店'],
                'package': f"{order['source_channel']}团购",
                '销售数量': 1,
                '销售金额': order['actual_amount'],
                '应收金额': order['should_amount'],
                '包含商品': ''
            })

    if not pkg_list:
        return {}

    pkg_df = pd.DataFrame(pkg_list)

    def get_first_product(x):
        products = [p for p in x if p]
        return products[0] if products else ''

    pkg_stats = pkg_df.groupby(['门店', 'package']).agg(
        销售数量=('销售数量', 'sum'),
        销售金额=('销售金额', 'sum'),
        应收金额=('应收金额', 'sum'),
        包含商品=('包含商品', get_first_product)
    ).reset_index()

    pkg_stats['单价'] = (pkg_stats['销售金额'] / pkg_stats['销售数量']).round(2)
    pkg_stats = pkg_stats.sort_values(['门店', '销售金额'], ascending=[True, False])

    pkg_dict = {}
    for s in pkg_stats['门店'].unique():
        pkg_dict[s] = pkg_stats[pkg_stats['门店'] == s].head(10)

    return pkg_dict


def calc_period_stats(od_df):
    if od_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    gb = od_df[od_df['is_groupbuy'] == 1]

    period = od_df.groupby(['门店', 'time_period']).agg(
        总订单数=('order_no', 'nunique'),
        总营收=('actual_amount', 'sum')
    ).reset_index()

    period_gb = gb.groupby(['门店', 'time_period']).agg(
        团购订单数=('order_no', 'nunique'),
        团购营收=('actual_amount', 'sum')
    ).reset_index() if not gb.empty else pd.DataFrame(columns=['门店', 'time_period', '团购订单数', '团购营收'])

    period = period.merge(period_gb, on=['门店', 'time_period'], how='left')
    for c in ['团购订单数', '团购营收']:
        period[c] = period[c].fillna(0)
    period['团购占比'] = (period['团购订单数'] / period['总订单数'] * 100).round(1)

    summary = od_df.groupby('门店').agg(
        总订单数=('order_no', 'nunique'),
        总营收=('actual_amount', 'sum')
    ).reset_index()
    summary_gb = gb.groupby('门店').agg(
        团购订单数=('order_no', 'nunique'),
        团购营收=('actual_amount', 'sum')
    ).reset_index() if not gb.empty else pd.DataFrame(columns=['门店', '团购订单数', '团购营收'])
    summary = summary.merge(summary_gb, on='门店', how='left')
    for c in ['团购订单数', '团购营收']:
        summary[c] = summary[c].fillna(0)
    summary['整体团购占比'] = (summary['团购订单数'] / summary['总订单数'] * 100).round(1)

    def classify(r):
        if r['整体团购占比'] >= 70:
            return '团购店'
        if r['整体团购占比'] >= 30:
            return '混合型'
        return '消费型'

    summary['门店类型'] = summary.apply(classify, axis=1)
    return summary, period


def fetch_period(period_df, store, name):
    d = period_df[(period_df['门店'] == store) & (period_df['time_period'] == name)]
    if d.empty:
        return 0, 0, 0.0
    r = d.iloc[0]
    return int(r['总订单数']), int(r['团购订单数']), float(r['团购占比'])


def generate_html_report(target_date, output_path=None):
    if output_path is None:
        output_path = OUTPUT_DIR / f"团购分析报告_{target_date}.html"

    od_df, gb_package_info = load_all_data(target_date)
    if od_df.empty:
        print(f"❌ {target_date} 无数据")
        return None

    pkg_dict = analyze_packages(od_df, gb_package_info)
    summary, period = calc_period_stats(od_df)

    stores = summary['门店'].nunique()
    to = summary['总订单数'].sum()
    go = summary['团购订单数'].sum()
    tr = summary['总营收'].sum()
    gr = summary['团购营收'].sum()
    gb_ratio = (go/to*100) if to > 0 else 0

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>团购分析报告 - {target_date}</title><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#333;background:#f5f5f5;line-height:1.6}}
.container{{max-width:1500px;margin:0 auto;background:#fff;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,.1)}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:25px;font-size:28px}}
h2{{color:#34495e;margin:35px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:20px}}
h3{{color:#4a6fa5;margin:20px 0 10px;font-size:16px}}
table{{width:100%;border-collapse:collapse;margin:15px 0;font-size:13px}}
th,td{{border:1px solid #ddd;padding:8px 10px;text-align:left}}
th{{background:#f0f8ff;font-weight:600;white-space:nowrap}}
tr:nth-child(even){{background:#f9f9f9}}
tr:hover{{background:#f0f0f0}}
.pos{{color:#28a745;font-weight:bold}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}}
.card{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:18px;border-radius:8px;text-align:center}}
.card.g{{background:linear-gradient(135deg,#11998e,#38ef7d)}}
.card.o{{background:linear-gradient(135deg,#f093fb,#f5576c)}}
.card.b{{background:linear-gradient(135deg,#4facfe,#00f2fe)}}
.card h3{{color:#fff;margin:0;font-size:13px;opacity:.9}}
.card .v{{font-size:26px;font-weight:bold;margin:8px 0}}
.sec{{margin-bottom:35px;padding-bottom:15px;border-bottom:2px solid #eee}}
.sec:last-child{{border-bottom:none;margin-bottom:0}}
.tag-g{{background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px}}
.tag-m{{background:#f39c12;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px}}
.tag-c{{background:#27ae60;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px}}
.footer{{text-align:center;color:#999;font-size:13px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}}
</style></head><body><div class="container">
<h1>团购分析报告 - {target_date}</h1>
<div style="color:#7f8c8d;margin-bottom:20px;font-size:13px;">
时段定义：<b>日场</b>(9:00-18:00) | <b>晚场</b>(18:00-24:00) | <b>午夜场</b>(0:00-9:00)<br>
团购判定：order_detail.source_channel ∈ {{'抖音', '美团大众', '线下团购'}}<br>
套餐价格：使用 order_detail.actual_amount（实收金额）
</div>

<div class="cards">
  <div class="card"><h3>统计门店</h3><div class="v">{stores}</div></div>
  <div class="card.g"><h3>总订单数</h3><div class="v">{to:,.0f}</div></div>
  <div class="card.o"><h3>团购订单数</h3><div class="v">{go:,.0f}</div></div>
  <div class="card.b"><h3>整体团购占比</h3><div class="v">{gb_ratio:.1f}%</div></div>
</div>
<div class="cards">
  <div class="card.g"><h3>总营收 (元)</h3><div class="v">{tr:,.2f}</div></div>
  <div class="card.o"><h3>团购营收 (元)</h3><div class="v">{gr:,.2f}</div></div>
</div>
"""

    s_sorted = summary.sort_values('整体团购占比', ascending=False)
    html += '<div class="sec"><h2>一、门店类型分布</h2><table>'
    html += '<tr><th>门店</th><th>总订单</th><th>团购订单</th><th>团购占比</th><th>总营收(元)</th><th>团购营收(元)</th><th>类型</th></tr>'
    for _, r in s_sorted.iterrows():
        tag = 'tag-g' if r['门店类型'] == '团购店' else ('tag-m' if r['门店类型'] == '混合型' else 'tag-c')
        html += f"<tr><td><b>{r['门店']}</b></td><td>{r['总订单数']:,.0f}</td><td class='pos'>{r['团购订单数']:,.0f}</td><td>{r['整体团购占比']:.1f}%</td><td>{r['总营收']:,.2f}</td><td class='pos'>{r['团购营收']:,.2f}</td><td><span class='{tag}'>{r['门店类型']}</span></td></tr>"
    html += '</table></div>'

    html += '<div class="sec"><h2>二、各门店团购套餐详情</h2>'
    if pkg_dict:
        for store in sorted(pkg_dict.keys()):
            pkgs = pkg_dict[store]
            html += f'<h3>{store} — 热销套餐</h3><table>'
            html += '<tr><th>#</th><th>套餐名称</th><th>销售数量</th><th>销售金额(元)</th><th>应收金额(元)</th><th>单价(元)</th><th>包含商品</th></tr>'
            for i, (_, p) in enumerate(pkgs.iterrows(), 1):
                html += f"<tr><td>{i}</td><td><b>{p['package']}</b></td><td>{p['销售数量']:,.0f}</td><td class='pos'>{p['销售金额']:,.2f}</td><td>{p['应收金额']:,.2f}</td><td class='pos'>{p['单价']:.2f}</td><td>{p['包含商品']}</td></tr>"
            html += '</table>'
    else:
        html += '<p>暂无团购套餐数据</p>'
    html += '</div>'

    html += '<div class="sec"><h2>三、各时段团购占比分析</h2><table>'
    html += '<tr><th>门店</th><th>日场 总订单</th><th>日场 团购</th><th>日场 %</th><th>晚场 总订单</th><th>晚场 团购</th><th>晚场 %</th><th>午夜 总订单</th><th>午夜 团购</th><th>午夜 %</th></tr>'
    for _, r in s_sorted.iterrows():
        s = r['门店']
        dt, dg, dr = fetch_period(period, s, '日场')
        et, eg, er = fetch_period(period, s, '晚场')
        nt, ng, nr = fetch_period(period, s, '午夜场')
        html += f"<tr><td><b>{s}</b></td><td>{dt}</td><td class='pos'>{dg}</td><td>{dr}%</td><td>{et}</td><td class='pos'>{eg}</td><td>{er}%</td><td>{nt}</td><td class='pos'>{ng}</td><td>{nr}%</td></tr>"
    html += '</table></div>'

    html += """<div class="sec"><h2>四、判断依据与说明</h2>
<ul style="margin-left:20px;line-height:2.2;font-size:14px;">
<li><b>团购店</b>：整体团购占比 ≥ 70% — 主要依赖团购引流</li>
<li><b>混合型</b>：30% ≤ 整体团购占比 &lt; 70% — 团购与自然消费均衡</li>
<li><b>消费型</b>：整体团购占比 &lt; 30% — 以自然消费为主</li>
</ul>
<h3>时段定义</h3><ul style="margin-left:20px;line-height:2;">
<li><b>日场</b>：open_time 9:00 - 17:59</li>
<li><b>晚场</b>：open_time 18:00 - 23:59</li>
<li><b>午夜场</b>：open_time 0:00 - 8:59</li>
</ul>
<h3>数据来源</h3><ul style="margin-left:20px;line-height:2;">
<li>订单 &amp; 团购判定：order_detail（source_channel = 抖音/美团大众/线下团购）</li>
<li>套餐金额：order_detail.actual_amount（实收金额）</li>
<li>套餐名称 &amp; 商品：product_sales_detail（通过 room_no 关联）</li>
</ul></div>
"""

    html += f"""<div class="footer">
团购分析报告 | 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} |
数据来源：order_detail + product_sales_detail | 糖果华庭 KTV
</div></div></body></html>"""

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
    p = argparse.ArgumentParser(description="生成团购分析报告")
    p.add_argument("date", nargs="?", help="目标日期 YYYY-MM-DD，默认昨天")
    a = p.parse_args()
    td = a.date or (date.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    generate_html_report(td)
