#!/usr/bin/env python3
"""
商品销售分析报告生成脚本
与综合看板商品分析页面保持一致
"""
import sys
from pathlib import Path
from datetime import datetime, date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import BIG_CATEGORIES, CATEGORY_MAP
from src.database import query

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

STORE_NAME_MERGE = {
    '上东': '上东',
    '上东店': '上东',
    '临河街': None,
    '临河街店': None,
    '总部': None,
    '总部店': None,
    '晨宇': '晨宇',
    '晨宇店': '晨宇',
    '通辽': '通辽',
    '通辽店': '通辽',
    '松原一': '松原一',
    '松原一店': '松原一',
    '松原二': '松原二',
    '松原二店': '松原二',
    '佳木斯': '佳木斯',
    '佳木斯店': '佳木斯',
    '鸡西': '鸡西',
    '鸡西店': '鸡西',
    '红旗街': '红旗街',
    '红旗街店': '红旗街',
    '安达': '安达',
    '安达店': '安达',
    '榆树': '榆树',
    '榆树店': '榆树',
    '法库': '法库',
    '法库店': '法库',
    '通化': '通化',
    '通化店': '通化',
}

def unify_store_name_for_product(name):
    if not name:
        return None
    name = str(name).strip()
    if name in STORE_NAME_MERGE:
        return STORE_NAME_MERGE[name]
    return name


def get_product_data(target_date):
    """获取商品销售数据"""
    sql = """
        SELECT
            p.product_name,
            p.big_category,
            p.category,
            p.unit_price,
            p.quantity,
            p.sales_amount,
            s.store_name
        FROM product_sales_summary p
        JOIN stores s ON p.store_id = s.id
        WHERE p.data_date = %s
    """
    df = query(sql, (target_date,))

    if not df.empty:
        df['mapped_category'] = df['big_category']
        df['门店'] = df['store_name'].apply(unify_store_name_for_product)
        df = df[df['门店'].notna()]

    return df


def calculate_metrics(df):
    """计算总览指标"""
    total_amount = df['sales_amount'].sum() / 10
    total_qty = df['quantity'].sum()
    total_products = df['product_name'].nunique()
    store_count = df['门店'].nunique()
    return {
        'store_count': store_count,
        'total_products': total_products,
        'total_qty': total_qty,
        'total_amount': total_amount
    }


def get_category_stats(df, total_amount):
    """获取分类统计"""
    category_stats = df.groupby('mapped_category').agg({
        'product_name': 'nunique',
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    category_stats.columns = ['分类', '商品数', '总数量', '总金额']
    category_stats['总金额'] = category_stats['总金额'] / 10
    category_stats['平均单价'] = category_stats['总金额'] / category_stats['总数量'] * 10
    category_stats['占比'] = category_stats['总金额'] / total_amount * 100
    category_stats['is_wine'] = (category_stats['分类'] == '酒水')
    category_stats = category_stats.sort_values(['is_wine', '总金额'], ascending=[False, False])
    category_stats = category_stats.drop('is_wine', axis=1)
    return category_stats


def get_store_category_summary(df):
    """获取各门店分类销售汇总"""
    store_cat_summary = df.groupby(['门店', 'mapped_category']).agg({
        'sales_amount': 'sum'
    }).reset_index()
    store_cat_summary.columns = ['门店', '分类', '金额']
    store_cat_summary['金额'] = store_cat_summary['金额'] / 10
    return store_cat_summary


def get_store_category_qty_summary(df):
    """获取各门店分类销量汇总"""
    store_qty_summary = df.groupby(['门店', 'mapped_category']).agg({
        'quantity': 'sum'
    }).reset_index()
    store_qty_summary.columns = ['门店', '分类', '销量']
    return store_qty_summary


def get_category_top10(df, category):
    """获取某分类的Top10商品"""
    cat_df = df[df['mapped_category'] == category]
    if cat_df.empty:
        return pd.DataFrame()

    top10 = cat_df.groupby('product_name').agg({
        'quantity': 'sum',
        'sales_amount': 'sum',
        '门店': 'nunique'
    }).reset_index()
    top10.columns = ['商品名称', '销售数量', '总销售额', '销售门店数']
    top10['总销售额'] = top10['总销售额'] / 10
    top10['平均单价'] = top10['总销售额'] * 10 / top10['销售数量']
    top10 = top10.sort_values('总销售额', ascending=False).head(10)
    return top10


def get_all_top10(df):
    """获取全品类Top10（排除"其他"分类）"""
    filtered_df = df[df['mapped_category'] != '其他']
    all_top10 = filtered_df.groupby(['product_name', 'mapped_category']).agg({
        'quantity': 'sum',
        'sales_amount': 'sum',
        '门店': 'nunique'
    }).reset_index()
    all_top10.columns = ['商品名称', '分类', '销售数量', '总销售额', '销售门店数']
    all_top10['总销售额'] = all_top10['总销售额'] / 10
    all_top10['平均单价'] = all_top10['总销售额'] * 10 / all_top10['销售数量']
    all_top10 = all_top10.sort_values('总销售额', ascending=False).head(10)
    return all_top10


def get_tongliao_data(df):
    """获取通辽店数据"""
    tongliao_df = df[df['门店'].str.contains('通辽', na=False)]
    if tongliao_df.empty:
        return None

    total_amount = tongliao_df['sales_amount'].sum() / 10
    total_qty = tongliao_df['quantity'].sum()

    category_stats = tongliao_df.groupby('mapped_category').agg({
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    category_stats.columns = ['分类', '销售数量', '销售金额']
    category_stats['销售金额'] = category_stats['销售金额'] / 10
    category_stats['占比'] = category_stats['销售金额'] / total_amount * 100
    category_stats = category_stats.sort_values('销售金额', ascending=False)

    top10 = tongliao_df.groupby('product_name').agg({
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    top10.columns = ['商品名称', '销售数量', '销售金额']
    top10['销售金额'] = top10['销售金额'] / 10
    top10['平均单价'] = top10['销售金额'] * 10 / top10['销售数量']
    top10 = top10.sort_values('销售金额', ascending=False).head(10)

    return {
        'total_amount': total_amount,
        'total_qty': total_qty,
        'category_stats': category_stats,
        'top10': top10
    }


def generate_html_report(target_date, output_path=None):
    """生成HTML报告"""
    if output_path is None:
        output_path = OUTPUT_DIR / f"商品销售分析报告_{target_date}.html"

    df = get_product_data(target_date)

    if df.empty:
        print(f"❌ {target_date} 无数据")
        return None

    metrics = calculate_metrics(df)
    category_stats = get_category_stats(df, metrics['total_amount'])
    store_cat_summary = get_store_category_summary(df)
    store_qty_summary = get_store_category_qty_summary(df)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>商品销售分析报告 - {target_date}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;line-height:1.6;color:#333;background:#f5f5f5}}
.container{{max-width:1400px;margin:0 auto;background:white;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:30px;font-size:28px}}
h2{{color:#34495e;margin:30px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:20px}}
h3{{color:#4a6fa5;margin:20px 0 10px;font-size:16px}}
table{{width:100%;border-collapse:collapse;margin:15px 0;background:white;font-size:14px}}
th,td{{border:1px solid #ddd;padding:10px 12px;text-align:left}}
th{{background:#f0f8ff;font-weight:600}}
tr:nth-child(even){{background:#f9f9f9}}
tr:hover{{background:#f5f5f5}}
.positive{{color:#28a745;font-weight:bold}}
.negative{{color:#dc3545;font-weight:bold}}
.footer{{text-align:center;color:#999;font-size:14px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}}
.summary-cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0}}
.summary-card{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px;border-radius:8px;text-align:center}}
.summary-card.green{{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%)}}
.summary-card.orange{{background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%)}}
.summary-card.blue{{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%)}}
.summary-card h3{{color:white;margin:0;font-size:14px;opacity:0.9}}
.summary-card .value{{font-size:28px;font-weight:bold;margin:10px 0}}
.section{{margin-bottom:40px;padding-bottom:20px;border-bottom:2px solid #eee}}
.section:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
</style>
</head>
<body>
<div class="container">
<h1>商品销售分析报告 - {target_date}</h1>
<div style="color:#7f8c8d;margin-bottom:20px;">数据来源：商品销售汇总（系统销售类别）</div>
<div class="summary-cards">
  <div class="summary-card"><h3>统计门店数</h3><div class="value">{metrics['store_count']}</div></div>
  <div class="summary-card green"><h3>总商品数</h3><div class="value">{metrics['total_products']}</div></div>
  <div class="summary-card orange"><h3>总销售数量</h3><div class="value">{metrics['total_qty']:,.0f}</div></div>
  <div class="summary-card blue"><h3>总销售金额</h3><div class="value">{metrics['total_amount']:,.2f}元</div></div>
</div>

<div class="section">
<h2>一、商品分类总览</h2>
<table>
<tr><th>分类</th><th>商品数</th><th>总数量</th><th>总金额 (元)</th><th>平均单价 (元)</th><th>占比</th></tr>
"""

    for _, row in category_stats.iterrows():
        html_content += f"""<tr><td>{row['分类']}</td><td>{row['商品数']}</td><td>{row['总数量']:,.0f}</td><td class="positive">{row['总金额']:,.2f}</td><td>{row['平均单价']:.2f}</td><td>{row['占比']:.1f}%</td></tr>
"""

    total_qty = category_stats['总数量'].sum()
    total_amount = category_stats['总金额'].sum()
    html_content += f"""<tr style="font-weight:bold;"><td>合计</td><td>{category_stats['商品数'].sum()}</td><td class="positive">{total_qty:,.0f}</td><td class="positive">{total_amount:,.2f}</td><td>{total_amount/total_qty:.2f}</td><td>100%</td></tr>
"""

    html_content += """</table>
</div>

<div class="section">
<h2>二、通辽店重点商品销售结构</h2>
"""

    tongliao_data = get_tongliao_data(df)
    if tongliao_data:
        html_content += f"""<p><strong>通辽店总销售额: {tongliao_data['total_amount']:,.2f}元</strong></p>
<table>
<tr><th>大分类</th><th>销售数量</th><th>销售金额(元)</th><th>占比</th></tr>
"""
        for _, row in tongliao_data['category_stats'].iterrows():
            html_content += f"""<tr><td>{row['分类']}</td><td>{row['销售数量']:,.0f}</td><td class="positive">{row['销售金额']:,.2f}</td><td>{row['占比']:.1f}%</td></tr>
"""
        html_content += f"""<tr style="font-weight:bold;"><td>合计</td><td>{tongliao_data['total_qty']:,.0f}</td><td class="positive">{tongliao_data['total_amount']:,.2f}</td><td>100%</td></tr>
</table>

<h3>通辽店 Top10 商品</h3>
<table>
<tr><th>排名</th><th>商品名称</th><th>销售数量</th><th>销售单价(元)</th><th>销售金额(元)</th></tr>
"""
        for rank, (_, row) in enumerate(tongliao_data['top10'].iterrows(), 1):
            html_content += f"""<tr><td>{rank}</td><td>{row['商品名称']}</td><td>{row['销售数量']:,.0f}</td><td>{row['平均单价']:.2f}</td><td class="positive">{row['销售金额']:.2f}</td></tr>
"""
        html_content += """</table>
"""
    else:
        html_content += """<p>暂无通辽店数据</p>
"""

    html_content += """</div>

<div class="section">
<h2>三、各门店分类销售对比（金额）</h2>
<table>
"""

    store_pivot = store_cat_summary.pivot(index='门店', columns='分类', values='金额').fillna(0)
    store_pivot['合计'] = store_pivot.sum(axis=1)
    store_pivot = store_pivot.sort_values('合计', ascending=False).head(15)

    ordered_cols = []
    for cat in BIG_CATEGORIES:
        if cat in store_pivot.columns:
            ordered_cols.append(cat)
    ordered_cols.append('合计')
    store_pivot = store_pivot[ordered_cols]

    # 动态生成表头
    html_content += "<tr><th>门店</th>"
    for col in ordered_cols:
        html_content += f"<th>{col}</th>"
    html_content += "</tr>\n"

    for idx, row in store_pivot.iterrows():
        html_content += f"<tr><td><strong>{idx}</strong></td>"
        for col in ordered_cols:
            if col in store_pivot.columns:
                val = row[col]
                if col == '合计':
                    html_content += f'<td class="positive">{val:,.0f}</td>'
                else:
                    html_content += f"<td>{val:,.0f}</td>"
            else:
                html_content += "<td>0</td>"
        html_content += "</tr>\n"

    html_content += """</table>
</div>

<div class="section">
<h2>四、各门店分类销量对比（数量）</h2>
<table>
"""

    store_qty_pivot = store_qty_summary.pivot(index='门店', columns='分类', values='销量').fillna(0)
    store_qty_pivot['合计'] = store_qty_pivot.sum(axis=1)
    store_qty_pivot = store_qty_pivot.sort_values('合计', ascending=False).head(15)

    ordered_cols_qty = []
    for cat in BIG_CATEGORIES:
        if cat in store_qty_pivot.columns:
            ordered_cols_qty.append(cat)
    ordered_cols_qty.append('合计')
    store_qty_pivot = store_qty_pivot[ordered_cols_qty]

    # 动态生成表头
    html_content += "<tr><th>门店</th>"
    for col in ordered_cols_qty:
        html_content += f"<th>{col}</th>"
    html_content += "</tr>\n"

    for idx, row in store_qty_pivot.iterrows():
        html_content += f"<tr><td><strong>{idx}</strong></td>"
        for col in ordered_cols_qty:
            if col in store_qty_pivot.columns:
                val = row[col]
                if col == '合计':
                    html_content += f'<td class="positive">{val:,.0f}</td>'
                else:
                    html_content += f"<td>{val:,.0f}</td>"
            else:
                html_content += "<td>0</td>"
        html_content += "</tr>\n"

    html_content += """</table>
</div>
"""

    categories = BIG_CATEGORIES
    for idx, cat in enumerate(categories, 1):
        cat_top10 = get_category_top10(df, cat)
        if not cat_top10.empty:
            html_content += f"""<div class="section">
<h2>五、{idx} {cat}类 Top10</h2>
<table>
<tr><th>排名</th><th>商品名称</th><th>销售数量</th><th>销售门店数</th><th>平均单价 (元)</th><th>总销售额 (元)</th></tr>
"""
            for rank, (_, row) in enumerate(cat_top10.iterrows(), 1):
                html_content += f"""<tr><td>{rank}</td><td>{row['商品名称']}</td><td>{row['销售数量']:,.0f}</td><td>{row['销售门店数']}</td><td>{row['平均单价']:.2f}</td><td><strong>{row['总销售额']:.2f}</strong></td></tr>
"""
            html_content += """</table>
</div>
"""

    all_top10 = get_all_top10(df)
    html_content += """<div class="section">
<h2>六、全品类 Top10</h2>
<table>
<tr><th>排名</th><th>商品名称</th><th>分类</th><th>销售数量</th><th>销售门店数</th><th>平均单价 (元)</th><th>总销售额 (元)</th></tr>
"""

    for rank, (_, row) in enumerate(all_top10.iterrows(), 1):
        html_content += f"""<tr><td>{rank}</td><td>{row['商品名称']}</td><td>{row['分类']}</td><td>{row['销售数量']:,.0f}</td><td>{row['销售门店数']}</td><td>{row['平均单价']:.2f}</td><td><strong>{row['总销售额']:.2f}</strong></td></tr>
"""

    html_content += """</table>
</div>

<div class="footer">商品销售分析报告 | 自动生成于 """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """ | 数据来源：糖果华庭 KTV 各门店</div>
</div>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    clear_extended_attributes(output_path)
    print(f"✅ 商品销售分析报告(HTML)已生成: {output_path}")

    # 自动生成PDF
    pdf_path = convert_html_to_pdf(output_path)
    if pdf_path:
        print(f"✅ PDF报告已生成: {pdf_path}")

    return output_path


def clear_extended_attributes(file_path: Path):
    """清除文件的扩展属性，避免访问权限问题"""
    import subprocess
    import os
    try:
        # 清除所有扩展属性
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
        # 确保文件权限正确
        os.chmod(str(file_path), 0o644)
        # 尝试清除隔离属性（针对macOS）
        try:
            subprocess.run(['xattr', '-d', 'com.apple.quarantine', str(file_path)], capture_output=True)
        except:
            pass
    except:
        pass


def convert_html_to_pdf(html_path: Path) -> Path:
    """使用Chrome headless模式将HTML转换为PDF - 优化版"""
    import time
    import subprocess
    from src.config import PROJECT_ROOT
    
    pdf_dir = PROJECT_ROOT / "data" / "output_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_name = html_path.stem + ".pdf"
    pdf_path = pdf_dir / pdf_name
    
    # 如果旧PDF存在，先删除
    if pdf_path.exists():
        try:
            pdf_path.unlink()
            time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ 删除旧PDF失败: {e}")
    
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
        print("   ⚠️ 未找到Chrome浏览器，跳过PDF生成")
        return None
    
    # 多次重试机制
    max_retries = 3
    for attempt in range(max_retries):
        # 使用新版headless模式，并添加更多参数避免权限问题
        cmd = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--disable-features=VizDisplayCompositor",
            f"--print-to-pdf={pdf_path.absolute()}",
            "--no-margins",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            str(html_path.absolute())
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # 等待文件系统完成写入
        time.sleep(1)
        
        if result.returncode == 0 and pdf_path.exists():
            # 检查文件大小是否稳定
            file_size_1 = pdf_path.stat().st_size
            time.sleep(0.5)
            file_size_2 = pdf_path.stat().st_size
            
            if file_size_1 == file_size_2 and file_size_1 > 1000:
                file_size_mb = file_size_1 / 1024 / 1024
                print(f"   ✅ PDF转换成功 (尝试 {attempt + 1}/{max_retries}): {pdf_name} ({file_size_mb:.2f} MB)")
                clear_extended_attributes(pdf_path)
                return pdf_path
        
        if attempt < max_retries - 1:
            print(f"   ⚠️ PDF转换失败 (尝试 {attempt + 1}/{max_retries})，将重试...")
            if pdf_path.exists():
                pdf_path.unlink()
            time.sleep(2)
    
    # 所有重试都失败
    print(f"   ❌ PDF转换失败 (尝试 {max_retries} 次): {result.stderr if result.stderr else '未知错误'}")
    if pdf_path.exists():
        pdf_path.unlink()
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成商品销售分析报告")
    parser.add_argument("date", nargs="?", help="目标日期 (YYYY-MM-DD)，默认昨天")
    args = parser.parse_args()

    target_date = args.date or (date.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    generate_html_report(target_date)