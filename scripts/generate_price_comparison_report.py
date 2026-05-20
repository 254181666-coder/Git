#!/usr/bin/env python3
"""
通辽店 vs 松原一店 商品价格体系对比分析报告
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.database import query

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def get_product_data(store_id, target_date):
    """获取指定门店指定日期的商品数据"""
    sql = """
        SELECT
            p.product_name,
            p.big_category,
            p.category,
            p.unit,
            p.unit_price,
            p.quantity,
            p.sales_amount
        FROM product_sales_summary p
        WHERE p.store_id = %s AND p.data_date = %s
    """
    df = query(sql, (store_id, target_date))
    return df


def get_data_range(store_id, days=7, end_date=None):
    """获取最近N天的数据"""
    if end_date is None:
        end_date = date.today() - timedelta(days=1)
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    start_date = end_date - timedelta(days=days-1)

    sql = """
        SELECT
            p.product_name,
            p.big_category,
            p.category,
            p.unit,
            p.unit_price,
            p.quantity,
            p.sales_amount
        FROM product_sales_summary p
        WHERE p.store_id = %s
        AND p.data_date BETWEEN %s AND %s
    """
    df = query(sql, (store_id, start_date, end_date))
    return df


def compare_same_products(tongliao_df, songyuan_df):
    """对比相同商品"""
    if tongliao_df.empty or songyuan_df.empty:
        return pd.DataFrame()

    tl = tongliao_df.groupby(['product_name', 'big_category', 'category', 'unit']).agg(
        unit_price_tl=('unit_price', 'mean'),
        quantity_tl=('quantity', 'sum'),
        sales_amount_tl=('sales_amount', 'sum')
    ).reset_index()

    sy = songyuan_df.groupby(['product_name', 'big_category', 'category', 'unit']).agg(
        unit_price_sy=('unit_price', 'mean'),
        quantity_sy=('quantity', 'sum'),
        sales_amount_sy=('sales_amount', 'sum')
    ).reset_index()

    merged = tl.merge(sy, on=['product_name', 'big_category', 'category', 'unit'], how='inner')
    merged = merged.sort_values('sales_amount_tl', ascending=False)
    return merged


def compare_category_avg(tongliao_df, songyuan_df):
    """对比分类平均价格"""
    def calculate_category_stats(df):
        if df.empty:
            return pd.DataFrame()
        return df.groupby(['big_category', 'category']).agg(
            商品数=('product_name', 'nunique'),
            平均价格=('unit_price', 'mean'),
            总销量=('quantity', 'sum'),
            总金额=('sales_amount', 'sum')
        ).reset_index()

    tl_cat = calculate_category_stats(tongliao_df)
    sy_cat = calculate_category_stats(songyuan_df)

    if tl_cat.empty or sy_cat.empty:
        return pd.DataFrame()

    tl_cat = tl_cat.rename(columns={
        '商品数': '商品数_通辽',
        '平均价格': '平均价格_通辽',
        '总销量': '总销量_通辽',
        '总金额': '总金额_通辽'
    })

    sy_cat = sy_cat.rename(columns={
        '商品数': '商品数_松原一',
        '平均价格': '平均价格_松原一',
        '总销量': '总销量_松原一',
        '总金额': '总金额_松原一'
    })

    merged = tl_cat.merge(sy_cat, on=['big_category', 'category'], how='outer')
    merged = merged.fillna(0)
    return merged


def get_top10_products(tongliao_df, songyuan_df):
    """获取热销Top10商品"""
    def get_top10(df, store_name):
        if df.empty:
            return pd.DataFrame()
        top10 = df.groupby(['product_name', 'big_category', 'category']).agg(
            总销量=('quantity', 'sum'),
            总金额=('sales_amount', 'sum'),
            平均单价=('unit_price', 'mean')
        ).reset_index()
        top10['总金额'] = top10['总金额'] / 10
        top10 = top10.sort_values('总金额', ascending=False).head(10)
        top10['门店'] = store_name
        return top10

    tl_top10 = get_top10(tongliao_df, '通辽')
    sy_top10 = get_top10(songyuan_df, '松原一')
    return tl_top10, sy_top10


def get_store_summary(tongliao_df, songyuan_df):
    """获取门店总体统计"""
    def get_summary(df):
        if df.empty:
            return {
                '商品数': 0,
                '总销量': 0,
                '总金额': 0,
                '分类数': 0
            }
        return {
            '商品数': df['product_name'].nunique(),
            '总销量': df['quantity'].sum(),
            '总金额': df['sales_amount'].sum() / 10,
            '分类数': df['big_category'].nunique()
        }

    return {
        '通辽': get_summary(tongliao_df),
        '松原一': get_summary(songyuan_df)
    }


def generate_html_report(target_date, days=1):
    """生成HTML报告"""
    if days > 1:
        end_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        start_date = end_date - timedelta(days=days-1)
        date_str = f"{start_date.strftime('%Y-%m-%d')}至{end_date.strftime('%Y-%m-%d')}"
        output_path = OUTPUT_DIR / f"通辽店VS松原一店_商品价格对比报告_{date_str}.html"
    else:
        date_str = target_date
        output_path = OUTPUT_DIR / f"通辽店VS松原一店_商品价格对比报告_{target_date}.html"

    if days > 1:
        tongliao_df = get_data_range(6, days, target_date)
        songyuan_df = get_data_range(10, days, target_date)
    else:
        tongliao_df = get_product_data(6, target_date)
        songyuan_df = get_product_data(10, target_date)
    
    tongliao_30d = get_data_range(6, 30, target_date)
    songyuan_30d = get_data_range(10, 30, target_date)

    same_products = compare_same_products(tongliao_df, songyuan_df)
    category_avg = compare_category_avg(tongliao_df, songyuan_df)
    tl_top10, sy_top10 = get_top10_products(tongliao_30d, songyuan_30d)
    summary = get_store_summary(tongliao_df, songyuan_df)

    html_lines = []
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html lang="zh-CN">')
    html_lines.append('<head>')
    html_lines.append('<meta charset="UTF-8">')
    html_lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    if days > 1:
        html_lines.append('<title>通辽店 vs 松原一店 商品价格对比报告 - ' + date_str + '</title>')
    else:
        html_lines.append('<title>通辽店 vs 松原一店 商品价格对比报告 - ' + target_date + '</title>')
    html_lines.append('<style>')
    html_lines.append('*{box-sizing:border-box;margin:0;padding:0}')
    html_lines.append('body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;line-height:1.6;color:#333;background:#f5f5f5}')
    html_lines.append('.container{max-width:1600px;margin:0 auto;background:white;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}')
    html_lines.append('h1{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:30px;font-size:28px}')
    html_lines.append('h2{color:#34495e;margin:30px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:20px}')
    html_lines.append('h3{color:#4a6fa5;margin:20px 0 10px;font-size:16px}')
    html_lines.append('table{width:100%;border-collapse:collapse;margin:15px 0;background:white;font-size:13px}')
    html_lines.append('th,td{border:1px solid #ddd;padding:8px 10px;text-align:center}')
    html_lines.append('th{background:#f0f8ff;font-weight:600}')
    html_lines.append('tr:nth-child(even){background:#f9f9f9}')
    html_lines.append('tr:hover{background:#f5f5f5}')
    html_lines.append('.positive{color:#28a745;font-weight:bold}')
    html_lines.append('.negative{color:#dc3545;font-weight:bold}')
    html_lines.append('.footer{text-align:center;color:#999;font-size:14px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}')
    html_lines.append('.section{margin-bottom:40px;padding-bottom:20px;border-bottom:2px solid #eee}')
    html_lines.append('.section:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}')
    html_lines.append('.summary-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0}')
    html_lines.append('.summary-card{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px;border-radius:8px;text-align:center}')
    html_lines.append('.summary-card.green{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%)}')
    html_lines.append('.summary-card.orange{background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%)}')
    html_lines.append('.summary-card.blue{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)}')
    html_lines.append('.summary-card h3{color:white;margin:0;font-size:14px;opacity:0.9}')
    html_lines.append('.summary-card .value{font-size:28px;font-weight:bold;margin:10px 0}')
    html_lines.append('.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}')
    html_lines.append('</style>')
    html_lines.append('</head>')
    html_lines.append('<body>')
    html_lines.append('<div class="container">')
    html_lines.append('<h1>通辽店 vs 松原一店 商品价格体系对比报告</h1>')
    html_lines.append('<div style="color:#7f8c8d;margin-bottom:20px;"><strong>对比日期:</strong> ' + date_str + ' | <strong>数据来源:</strong> 商品销售汇总</div>')
    html_lines.append('<div class="summary-cards">')
    html_lines.append('<div class="summary-card">')
    html_lines.append('<h3>通辽店商品数</h3>')
    html_lines.append('<div class="value">' + str(summary['通辽']['商品数']) + '</div>')
    html_lines.append('</div>')
    html_lines.append('<div class="summary-card green">')
    html_lines.append('<h3>松原一店商品数</h3>')
    html_lines.append('<div class="value">' + str(summary['松原一']['商品数']) + '</div>')
    html_lines.append('</div>')
    html_lines.append('<div class="summary-card orange">')
    html_lines.append('<h3>通辽店销售额</h3>')
    html_lines.append('<div class="value">' + '{:,.2f}'.format(summary['通辽']['总金额']) + '元</div>')
    html_lines.append('</div>')
    html_lines.append('<div class="summary-card blue">')
    html_lines.append('<h3>松原一店销售额</h3>')
    html_lines.append('<div class="value">' + '{:,.2f}'.format(summary['松原一']['总金额']) + '元</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')

    html_lines.append('<div class="section">')
    html_lines.append('<h2>一、相同商品价格对比</h2>')

    if not same_products.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>商品名称</th><th>大分类</th><th>小分类</th><th>单位</th><th>通辽店价格(元)</th><th>松原一店价格(元)</th><th>价格差(元)</th><th>价格差异率(%)</th></tr>')
        for _, row in same_products.iterrows():
            diff = row['unit_price_tl'] - row['unit_price_sy']
            diff_rate = ((row['unit_price_tl'] / row['unit_price_sy']) - 1) * 100
            diff_color = 'positive' if diff >= 0 else 'negative'
            html_lines.append('<tr><td>' + row['product_name'] + '</td><td>' + row['big_category'] + '</td><td>' + row['category'] + '</td><td>' + str(row['unit']) + '</td><td>' + '{:.2f}'.format(row['unit_price_tl']) + '</td><td>' + '{:.2f}'.format(row['unit_price_sy']) + '</td><td class="' + diff_color + '">' + '{:+.2f}'.format(diff) + '</td><td class="' + diff_color + '">' + '{:+.2f}'.format(diff_rate) + '</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无相同商品数据</p>')

    html_lines.append('</div>')

    html_lines.append('<div class="section">')
    html_lines.append('<h2>二、重点分类平均价格对比</h2>')

    if not category_avg.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>小分类</th><th>通辽店商品数</th><th>松原一店商品数</th><th>通辽店平均价格(元)</th><th>松原一店平均价格(元)</th><th>平均价格差(元)</th><th>平均价格差异率(%)</th></tr>')
        for _, row in category_avg.iterrows():
            diff = row['平均价格_通辽'] - row['平均价格_松原一']
            if row['平均价格_松原一'] > 0:
                diff_rate = ((row['平均价格_通辽'] / row['平均价格_松原一']) - 1) * 100
            else:
                diff_rate = 0
            diff_color = 'positive' if diff >= 0 else 'negative'
            html_lines.append('<tr><td>' + str(row['big_category']) + '</td><td>' + str(row['category']) + '</td><td>' + str(int(row['商品数_通辽'])) + '</td><td>' + str(int(row['商品数_松原一'])) + '</td><td>' + '{:.2f}'.format(row['平均价格_通辽']) + '</td><td>' + '{:.2f}'.format(row['平均价格_松原一']) + '</td><td class="' + diff_color + '">' + '{:+.2f}'.format(diff) + '</td><td class="' + diff_color + '">' + '{:+.2f}'.format(diff_rate) + '</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无分类数据</p>')

    html_lines.append('</div>')

    html_lines.append('<div class="section">')
    html_lines.append('<h2>三、热销Top10商品对比</h2>')
    html_lines.append('<div class="two-col">')
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店 Top10（最近30天）</h3>')

    if not tl_top10.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>排名</th><th>商品名称</th><th>大分类</th><th>小分类</th><th>平均单价(元)</th><th>总销量</th><th>总金额(元)</th></tr>')
        for rank, (_, row) in enumerate(tl_top10.iterrows(), 1):
            html_lines.append('<tr><td>' + str(rank) + '</td><td>' + row['product_name'] + '</td><td>' + row['big_category'] + '</td><td>' + row['category'] + '</td><td>' + '{:.2f}'.format(row['平均单价']) + '</td><td>' + '{:,}'.format(int(row['总销量'])) + '</td><td class="positive">' + '{:.2f}'.format(row['总金额']) + '</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无通辽店数据</p>')

    html_lines.append('</div>')
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店 Top10（最近30天）</h3>')

    if not sy_top10.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>排名</th><th>商品名称</th><th>大分类</th><th>小分类</th><th>平均单价(元)</th><th>总销量</th><th>总金额(元)</th></tr>')
        for rank, (_, row) in enumerate(sy_top10.iterrows(), 1):
            html_lines.append('<tr><td>' + str(rank) + '</td><td>' + row['product_name'] + '</td><td>' + row['big_category'] + '</td><td>' + row['category'] + '</td><td>' + '{:.2f}'.format(row['平均单价']) + '</td><td>' + '{:,}'.format(int(row['总销量'])) + '</td><td class="positive">' + '{:.2f}'.format(row['总金额']) + '</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无松原一店数据</p>')

    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')

    html_lines.append('<div class="section">')
    html_lines.append('<h2>四、商品结构对比</h2>')

    def get_big_cat_stats(df):
        if df.empty:
            return pd.DataFrame()
        stats = df.groupby('big_category').agg(
            商品数=('product_name', 'nunique'),
            总销量=('quantity', 'sum'),
            总金额=('sales_amount', 'sum'),
            平均价格=('unit_price', 'mean')
        ).reset_index()
        stats['总金额'] = stats['总金额'] / 10
        return stats

    tl_bigcat = get_big_cat_stats(tongliao_df)
    sy_bigcat = get_big_cat_stats(songyuan_df)

    html_lines.append('<div class="two-col">')
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店商品结构</h3>')

    if not tl_bigcat.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>商品数</th><th>总销量</th><th>总金额(元)</th><th>平均价格(元)</th></tr>')
        tl_total = tl_bigcat['总金额'].sum()
        for _, row in tl_bigcat.iterrows():
            html_lines.append('<tr><td>' + row['big_category'] + '</td><td>' + str(row['商品数']) + '</td><td>' + '{:,}'.format(int(row['总销量'])) + '</td><td class="positive">' + '{:.2f}'.format(row['总金额']) + '</td><td>' + '{:.2f}'.format(row['平均价格']) + '</td></tr>')
        html_lines.append('<tr style="font-weight:bold;"><td>合计</td><td>' + str(tl_bigcat['商品数'].sum()) + '</td><td>' + '{:,}'.format(int(tl_bigcat['总销量'].sum())) + '</td><td class="positive">' + '{:.2f}'.format(tl_total) + '</td><td>-</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')

    html_lines.append('</div>')
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店商品结构</h3>')

    if not sy_bigcat.empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>商品数</th><th>总销量</th><th>总金额(元)</th><th>平均价格(元)</th></tr>')
        sy_total = sy_bigcat['总金额'].sum()
        for _, row in sy_bigcat.iterrows():
            html_lines.append('<tr><td>' + row['big_category'] + '</td><td>' + str(row['商品数']) + '</td><td>' + '{:,}'.format(int(row['总销量'])) + '</td><td class="positive">' + '{:.2f}'.format(row['总金额']) + '</td><td>' + '{:.2f}'.format(row['平均价格']) + '</td></tr>')
        html_lines.append('<tr style="font-weight:bold;"><td>合计</td><td>' + str(sy_bigcat['商品数'].sum()) + '</td><td>' + '{:,}'.format(int(sy_bigcat['总销量'].sum())) + '</td><td class="positive">' + '{:.2f}'.format(sy_total) + '</td><td>-</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')

    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')

    html_lines.append('<div class="footer">通辽店 vs 松原一店 商品价格对比报告 | 自动生成于 ' + datetime.now().strftime('%Y-%m-%d %H:%M') + ' | 数据来源：糖果华庭 KTV</div>')
    html_lines.append('</div>')
    html_lines.append('</body>')
    html_lines.append('</html>')

    html_content = '\n'.join(html_lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print('✅ 对比报告(HTML)已生成:', output_path)

    pdf_path = convert_html_to_pdf(output_path)
    if pdf_path:
        print('✅ PDF报告已生成:', pdf_path)

    return output_path


def clear_extended_attributes(file_path):
    """清除文件的扩展属性"""
    import subprocess
    try:
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
    except:
        pass


def convert_html_to_pdf(html_path):
    """使用Chrome headless模式将HTML转换为PDF"""
    pdf_dir = PROJECT_ROOT / "data" / "output_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    pdf_name = html_path.stem + ".pdf"
    pdf_path = pdf_dir / pdf_name

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
    ]

    chrome_path = None
    for path in chrome_paths:
        if Path(path).exists():
            chrome_path = path
            break

    if not chrome_path:
        print('   ⚠️ 未找到Chrome浏览器，跳过PDF生成')
        return None

    cmd = [
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-software-rasterizer",
        f"--print-to-pdf={pdf_path.absolute()}",
        "--no-margins",
        "--disable-dev-shm-usage",
        str(html_path.absolute())
    ]

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
        file_size = pdf_path.stat().st_size / 1024 / 1024
        print(f'   ✅ PDF转换成功: {pdf_name} ({file_size:.2f} MB)')
        clear_extended_attributes(pdf_path)
        return pdf_path
    else:
        print(f'   ⚠️ PDF转换失败: {result.stderr if result.stderr else "未知错误"}')
        if pdf_path.exists():
            pdf_path.unlink()
        return None


def main():
    target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    days = 1

    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    if len(sys.argv) > 2:
        days = int(sys.argv[2])

    if days > 1:
        end_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        start_date = end_date - timedelta(days=days-1)
        print(f'📅 生成通辽店 vs 松原一店 商品价格对比报告: {start_date.strftime("%Y-%m-%d")}至{end_date.strftime("%Y-%m-%d")}')
    else:
        print('📅 生成通辽店 vs 松原一店 商品价格对比报告:', target_date)

    html_path = generate_html_report(target_date, days)

    print('✅ 报告生成完成!')


if __name__ == "__main__":
    main()
