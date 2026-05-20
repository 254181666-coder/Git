#!/usr/bin/env python3
"""
通辽店 vs 松原一店 - 人员提成与商品销售覆盖率对比分析
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from src.config import BIG_CATEGORIES
from src.database import query

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# 门店ID映射
STORE_IDS = {
    '通辽': 6,
    '松原一': 10
}


def get_date_range(days=30):
    """获取日期范围"""
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    return start_date, end_date


def get_commission_data(store_id, start_date, end_date):
    """获取人员提成数据"""
    sql = """
        SELECT
            sc.business_date,
            sc.commission_staff,
            sc.staff_account,
            sc.stored_amount,
            sc.commission_amount,
            sc.commission_rule
        FROM stored_commission sc
        WHERE sc.store_id = %s
          AND sc.business_date BETWEEN %s AND %s
    """
    df = query(sql, (store_id, start_date, end_date))
    return df


def analyze_commission(commission_df, store_name):
    """分析人员提成数据"""
    if commission_df.empty:
        return {
            'store_name': store_name,
            'total_commission': 0,
            'total_stored': 0,
            'staff_count': 0,
            'transaction_count': 0,
            'staff_details': pd.DataFrame(),
            'daily_stats': pd.DataFrame()
        }
    
    # 按员工统计
    staff_stats = commission_df.groupby('commission_staff').agg({
        'commission_amount': 'sum',
        'stored_amount': 'sum',
        'business_date': 'count'
    }).reset_index()
    staff_stats.columns = ['员工姓名', '提成总额', '储值总额', '交易次数']
    staff_stats['提成效率'] = staff_stats['提成总额'] / staff_stats['交易次数']
    staff_stats = staff_stats.sort_values('提成总额', ascending=False)
    
    # 按日期统计
    daily_stats = commission_df.groupby('business_date').agg({
        'commission_amount': 'sum',
        'stored_amount': 'sum',
        'commission_staff': 'nunique'
    }).reset_index()
    daily_stats['交易次数'] = commission_df.groupby('business_date').size().values
    daily_stats.columns = ['日期', '当日提成', '当日储值', '当日员工数', '当日交易数']
    daily_stats = daily_stats.sort_values('日期')
    
    return {
        'store_name': store_name,
        'total_commission': commission_df['commission_amount'].sum(),
        'total_stored': commission_df['stored_amount'].sum(),
        'staff_count': commission_df['commission_staff'].nunique(),
        'transaction_count': len(commission_df),
        'staff_details': staff_stats,
        'daily_stats': daily_stats
    }


def get_product_coverage_data(store_id, start_date, end_date):
    """获取商品销售覆盖率数据 - 按包房统计"""
    # 先获取商品明细数据
    sql_detail = """
        SELECT
            p.data_date,
            p.room_no,
            p.product_name,
            p.quantity,
            p.sales_amount
        FROM product_sales_detail p
        WHERE p.store_id = %s
          AND p.data_date BETWEEN %s AND %s
    """
    df_detail = query(sql_detail, (store_id, start_date, end_date))
    
    if df_detail.empty:
        return df_detail
    
    # 再获取商品分类信息（从 product_sales_summary 表）
    sql_category = """
        SELECT DISTINCT
            p.product_name,
            p.big_category
        FROM product_sales_summary p
        WHERE p.store_id = %s
          AND p.data_date BETWEEN %s AND %s
    """
    df_category = query(sql_category, (store_id, start_date, end_date))
    
    # 合并数据
    if not df_category.empty:
        df = df_detail.merge(df_category, on='product_name', how='left')
        # 对于没有匹配到分类的商品，标记为"其他"
        df['big_category'] = df['big_category'].fillna('其他')
    else:
        df_detail['big_category'] = '其他'
        df = df_detail
    
    return df


def analyze_product_coverage(product_df, store_name, start_date, end_date):
    """分析商品销售覆盖率 - 按重点分类统计包房覆盖率，分工作日/周末"""
    if product_df.empty:
        return {
            'store_name': store_name,
            'total_rooms': 0,
            'total_categories': 0,
            'total_quantity': 0,
            'total_amount': 0,
            'category_coverage': pd.DataFrame(),
            'category_sales': pd.DataFrame(),
            'daily_room_count': pd.DataFrame(),
            'weekday_coverage': pd.DataFrame(),
            'weekend_coverage': pd.DataFrame()
        }
    
    # 确保 data_date 是日期类型
    product_df['data_date'] = pd.to_datetime(product_df['data_date'])
    
    # 获取星期几 (0=周一, 6=周日)
    product_df['weekday'] = product_df['data_date'].dt.dayofweek
    
    # 定义工作日和周末：周一(0)-周四(3)、周日(6) 为工作日；周五(4)-周六(5) 为周末
    product_df['period'] = product_df['weekday'].apply(
        lambda x: '工作日' if x in [0, 1, 2, 3, 6] else '周末'
    )
    
    # 总包房数（有销售记录的包房数）
    total_rooms = product_df['room_no'].nunique()
    
    # 分类覆盖率统计 - 每个分类在多少个包房中销售过（整体）
    category_coverage = product_df.groupby('big_category').agg({
        'room_no': 'nunique',
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    category_coverage.columns = ['大分类', '覆盖包房数', '销售数量', '销售金额']
    category_coverage['销售金额'] = category_coverage['销售金额'] / 10
    category_coverage['覆盖率'] = category_coverage['覆盖包房数'] / total_rooms * 100
    category_coverage = category_coverage.sort_values('覆盖率', ascending=False)
    
    # 分类销售统计 - 只看重点分类
    category_sales = product_df.groupby('big_category').agg({
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    category_sales.columns = ['大分类', '销售数量', '销售金额']
    category_sales['销售金额'] = category_sales['销售金额'] / 10
    category_sales = category_sales.sort_values('销售金额', ascending=False)
    
    # 每日包房数统计
    daily_room_count = product_df.groupby('data_date').agg({
        'room_no': 'nunique',
        'quantity': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    daily_room_count.columns = ['日期', '当日有销售的包房数', '当日销量', '当日销售额']
    daily_room_count['当日销售额'] = daily_room_count['当日销售额'] / 10
    daily_room_count = daily_room_count.sort_values('日期')
    
    # 按工作日/周末分别统计分类覆盖率
    def calculate_coverage_by_period(df, period_name):
        period_df = df[df['period'] == period_name]
        if period_df.empty:
            return pd.DataFrame()
        
        period_rooms = period_df['room_no'].nunique()
        if period_rooms == 0:
            return pd.DataFrame()
        
        period_coverage = period_df.groupby('big_category').agg({
            'room_no': 'nunique',
            'quantity': 'sum',
            'sales_amount': 'sum'
        }).reset_index()
        period_coverage.columns = ['大分类', '覆盖包房数', '销售数量', '销售金额']
        period_coverage['销售金额'] = period_coverage['销售金额'] / 10
        period_coverage['覆盖率'] = period_coverage['覆盖包房数'] / period_rooms * 100
        period_coverage = period_coverage.sort_values('覆盖率', ascending=False)
        return period_coverage
    
    weekday_coverage = calculate_coverage_by_period(product_df, '工作日')
    weekend_coverage = calculate_coverage_by_period(product_df, '周末')
    
    return {
        'store_name': store_name,
        'total_rooms': total_rooms,
        'total_categories': product_df['big_category'].nunique(),
        'total_quantity': product_df['quantity'].sum(),
        'total_amount': product_df['sales_amount'].sum() / 10,
        'category_coverage': category_coverage,
        'category_sales': category_sales,
        'daily_room_count': daily_room_count,
        'weekday_coverage': weekday_coverage,
        'weekend_coverage': weekend_coverage
    }


def clear_extended_attributes(file_path: Path):
    """清除文件的扩展属性，避免访问权限问题"""
    import subprocess
    try:
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
    except:
        pass


def convert_html_to_pdf(html_path: Path) -> Path:
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


def generate_html_report(start_date, end_date, tongliao_commission, songyuan_commission,
                          tongliao_coverage, songyuan_coverage):
    """生成HTML报告"""
    date_str = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
    output_path = OUTPUT_DIR / f"通辽店vs松原一店_提成与覆盖率分析_{date_str}.html"
    
    html_lines = []
    html_lines.append('<!DOCTYPE html>')
    html_lines.append('<html lang="zh-CN">')
    html_lines.append('<head>')
    html_lines.append('<meta charset="UTF-8">')
    html_lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_lines.append(f'<title>通辽店 vs 松原一店 - 提成与覆盖率分析报告 - {date_str}</title>')
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
    html_lines.append(f'<h1>通辽店 vs 松原一店 - 提成与覆盖率分析报告</h1>')
    html_lines.append(f'<div style="color:#7f8c8d;margin-bottom:20px;"><strong>分析周期:</strong> {date_str}</div>')
    
    # 总体概览
    html_lines.append('<div class="section">')
    html_lines.append('<h2>一、总体概览</h2>')
    html_lines.append('<div class="two-col">')
    
    # 提成概览
    html_lines.append('<div>')
    html_lines.append('<h3>人员提成对比</h3>')
    html_lines.append('<table>')
    html_lines.append('<tr><th>指标</th><th>通辽店</th><th>松原一店</th><th>差异</th></tr>')
    html_lines.append(f'<tr><td>总提成金额</td><td class="positive">{tongliao_commission["total_commission"]:,.2f}元</td><td class="positive">{songyuan_commission["total_commission"]:,.2f}元</td><td class="{"positive" if tongliao_commission["total_commission"] >= songyuan_commission["total_commission"] else "negative"}">{tongliao_commission["total_commission"] - songyuan_commission["total_commission"]:,.2f}元</td></tr>')
    html_lines.append(f'<tr><td>总储值金额</td><td class="positive">{tongliao_commission["total_stored"]:,.2f}元</td><td class="positive">{songyuan_commission["total_stored"]:,.2f}元</td><td class="{"positive" if tongliao_commission["total_stored"] >= songyuan_commission["total_stored"] else "negative"}">{tongliao_commission["total_stored"] - songyuan_commission["total_stored"]:,.2f}元</td></tr>')
    html_lines.append(f'<tr><td>参与员工数</td><td>{tongliao_commission["staff_count"]}人</td><td>{songyuan_commission["staff_count"]}人</td><td class="{"positive" if tongliao_commission["staff_count"] >= songyuan_commission["staff_count"] else "negative"}">{tongliao_commission["staff_count"] - songyuan_commission["staff_count"]}人</td></tr>')
    html_lines.append(f'<tr><td>交易次数</td><td>{tongliao_commission["transaction_count"]}次</td><td>{songyuan_commission["transaction_count"]}次</td><td class="{"positive" if tongliao_commission["transaction_count"] >= songyuan_commission["transaction_count"] else "negative"}">{tongliao_commission["transaction_count"] - songyuan_commission["transaction_count"]}次</td></tr>')
    html_lines.append('</table>')
    html_lines.append('</div>')
    
    # 商品覆盖率概览
    html_lines.append('<div>')
    html_lines.append('<h3>商品销售覆盖率对比（按包房统计）</h3>')
    html_lines.append('<table>')
    html_lines.append('<tr><th>指标</th><th>通辽店</th><th>松原一店</th><th>差异</th></tr>')
    html_lines.append(f'<tr><td>有销售的包房数</td><td>{tongliao_coverage["total_rooms"]}个</td><td>{songyuan_coverage["total_rooms"]}个</td><td class="{"positive" if tongliao_coverage["total_rooms"] >= songyuan_coverage["total_rooms"] else "negative"}">{tongliao_coverage["total_rooms"] - songyuan_coverage["total_rooms"]}个</td></tr>')
    html_lines.append(f'<tr><td>覆盖分类数</td><td>{tongliao_coverage["total_categories"]}类</td><td>{songyuan_coverage["total_categories"]}类</td><td class="{"positive" if tongliao_coverage["total_categories"] >= songyuan_coverage["total_categories"] else "negative"}">{tongliao_coverage["total_categories"] - songyuan_coverage["total_categories"]}类</td></tr>')
    html_lines.append(f'<tr><td>总销售数量</td><td>{tongliao_coverage["total_quantity"]:,.0f}</td><td>{songyuan_coverage["total_quantity"]:,.0f}</td><td class="{"positive" if tongliao_coverage["total_quantity"] >= songyuan_coverage["total_quantity"] else "negative"}">{tongliao_coverage["total_quantity"] - songyuan_coverage["total_quantity"]:,.0f}</td></tr>')
    html_lines.append(f'<tr><td>总销售金额</td><td class="positive">{tongliao_coverage["total_amount"]:,.2f}元</td><td class="positive">{songyuan_coverage["total_amount"]:,.2f}元</td><td class="{"positive" if tongliao_coverage["total_amount"] >= songyuan_coverage["total_amount"] else "negative"}">{tongliao_coverage["total_amount"] - songyuan_coverage["total_amount"]:,.2f}元</td></tr>')
    html_lines.append('</table>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    
    # 人员提成详细分析
    html_lines.append('<div class="section">')
    html_lines.append('<h2>二、人员提成详细分析</h2>')
    html_lines.append('<div class="two-col">')
    
    # 通辽店员工提成
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店 - 员工提成排行</h3>')
    if not tongliao_commission['staff_details'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>排名</th><th>员工姓名</th><th>提成总额(元)</th><th>储值总额(元)</th><th>交易次数</th><th>平均每次提成(元)</th></tr>')
        for rank, (_, row) in enumerate(tongliao_commission['staff_details'].iterrows(), 1):
            html_lines.append(f'<tr><td>{rank}</td><td>{row["员工姓名"]}</td><td class="positive">{row["提成总额"]:,.2f}</td><td>{row["储值总额"]:,.2f}</td><td>{row["交易次数"]}</td><td>{row["提成效率"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    
    # 松原一店员工提成
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店 - 员工提成排行</h3>')
    if not songyuan_commission['staff_details'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>排名</th><th>员工姓名</th><th>提成总额(元)</th><th>储值总额(元)</th><th>交易次数</th><th>平均每次提成(元)</th></tr>')
        for rank, (_, row) in enumerate(songyuan_commission['staff_details'].iterrows(), 1):
            html_lines.append(f'<tr><td>{rank}</td><td>{row["员工姓名"]}</td><td class="positive">{row["提成总额"]:,.2f}</td><td>{row["储值总额"]:,.2f}</td><td>{row["交易次数"]}</td><td>{row["提成效率"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    
    # 商品销售覆盖率详细分析
    html_lines.append('<div class="section">')
    html_lines.append('<h2>三、重点分类包房覆盖率详细分析</h2>')
    html_lines.append('<div class="two-col">')
    
    # 通辽店分类覆盖率
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店 - 重点分类包房覆盖率</h3>')
    if not tongliao_coverage['category_coverage'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>覆盖包房数</th><th>覆盖率</th><th>销售数量</th><th>销售金额(元)</th></tr>')
        for _, row in tongliao_coverage['category_coverage'].iterrows():
            html_lines.append(f'<tr><td>{row["大分类"]}</td><td>{row["覆盖包房数"]}</td><td>{row["覆盖率"]:.1f}%</td><td>{row["销售数量"]:,.0f}</td><td class="positive">{row["销售金额"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    
    # 松原一店分类覆盖率
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店 - 重点分类包房覆盖率</h3>')
    if not songyuan_coverage['category_coverage'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>覆盖包房数</th><th>覆盖率</th><th>销售数量</th><th>销售金额(元)</th></tr>')
        for _, row in songyuan_coverage['category_coverage'].iterrows():
            html_lines.append(f'<tr><td>{row["大分类"]}</td><td>{row["覆盖包房数"]}</td><td>{row["覆盖率"]:.1f}%</td><td>{row["销售数量"]:,.0f}</td><td class="positive">{row["销售金额"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    
    # 分类销售对比
    html_lines.append('<div class="section">')
    html_lines.append('<h2>四、重点分类销售对比</h2>')
    html_lines.append('<div class="two-col">')
    
    # 通辽店分类销售
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店 - 分类销售统计</h3>')
    if not tongliao_coverage['category_sales'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>销售数量</th><th>销售金额(元)</th></tr>')
        for _, row in tongliao_coverage['category_sales'].iterrows():
            html_lines.append(f'<tr><td>{row["大分类"]}</td><td>{row["销售数量"]:,.0f}</td><td class="positive">{row["销售金额"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    
    # 松原一店分类销售
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店 - 分类销售统计</h3>')
    if not songyuan_coverage['category_sales'].empty:
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>销售数量</th><th>销售金额(元)</th></tr>')
        for _, row in songyuan_coverage['category_sales'].iterrows():
            html_lines.append(f'<tr><td>{row["大分类"]}</td><td>{row["销售数量"]:,.0f}</td><td class="positive">{row["销售金额"]:,.2f}</td></tr>')
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    
    # 工作日/周末覆盖率对比
    html_lines.append('<div class="section">')
    html_lines.append('<h2>五、工作日/周末分类包房覆盖率对比</h2>')
    html_lines.append('<div class="two-col">')
    
    # 通辽店工作日/周末对比
    html_lines.append('<div>')
    html_lines.append('<h3>通辽店 - 工作日 vs 周末</h3>')
    
    if not tongliao_coverage['weekday_coverage'].empty or not tongliao_coverage['weekend_coverage'].empty:
        # 获取所有分类
        all_categories = set()
        if not tongliao_coverage['weekday_coverage'].empty:
            all_categories.update(tongliao_coverage['weekday_coverage']['大分类'].tolist())
        if not tongliao_coverage['weekend_coverage'].empty:
            all_categories.update(tongliao_coverage['weekend_coverage']['大分类'].tolist())
        
        # 创建合并数据
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>工作日覆盖率</th><th>周末覆盖率</th><th>差异</th></tr>')
        
        for cat in sorted(all_categories):
            wk_coverage = 0
            we_coverage = 0
            
            if not tongliao_coverage['weekday_coverage'].empty:
                wk_row = tongliao_coverage['weekday_coverage'][tongliao_coverage['weekday_coverage']['大分类'] == cat]
                if not wk_row.empty:
                    wk_coverage = wk_row.iloc[0]['覆盖率']
            
            if not tongliao_coverage['weekend_coverage'].empty:
                we_row = tongliao_coverage['weekend_coverage'][tongliao_coverage['weekend_coverage']['大分类'] == cat]
                if not we_row.empty:
                    we_coverage = we_row.iloc[0]['覆盖率']
            
            diff = we_coverage - wk_coverage
            diff_class = 'positive' if diff >= 0 else 'negative'
            html_lines.append(f'<tr><td>{cat}</td><td>{wk_coverage:.1f}%</td><td>{we_coverage:.1f}%</td><td class="{diff_class}">{diff:+.1f}%</td></tr>')
        
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    
    # 松原一店工作日/周末对比
    html_lines.append('<div>')
    html_lines.append('<h3>松原一店 - 工作日 vs 周末</h3>')
    
    if not songyuan_coverage['weekday_coverage'].empty or not songyuan_coverage['weekend_coverage'].empty:
        # 获取所有分类
        all_categories = set()
        if not songyuan_coverage['weekday_coverage'].empty:
            all_categories.update(songyuan_coverage['weekday_coverage']['大分类'].tolist())
        if not songyuan_coverage['weekend_coverage'].empty:
            all_categories.update(songyuan_coverage['weekend_coverage']['大分类'].tolist())
        
        # 创建合并数据
        html_lines.append('<table>')
        html_lines.append('<tr><th>大分类</th><th>工作日覆盖率</th><th>周末覆盖率</th><th>差异</th></tr>')
        
        for cat in sorted(all_categories):
            wk_coverage = 0
            we_coverage = 0
            
            if not songyuan_coverage['weekday_coverage'].empty:
                wk_row = songyuan_coverage['weekday_coverage'][songyuan_coverage['weekday_coverage']['大分类'] == cat]
                if not wk_row.empty:
                    wk_coverage = wk_row.iloc[0]['覆盖率']
            
            if not songyuan_coverage['weekend_coverage'].empty:
                we_row = songyuan_coverage['weekend_coverage'][songyuan_coverage['weekend_coverage']['大分类'] == cat]
                if not we_row.empty:
                    we_coverage = we_row.iloc[0]['覆盖率']
            
            diff = we_coverage - wk_coverage
            diff_class = 'positive' if diff >= 0 else 'negative'
            html_lines.append(f'<tr><td>{cat}</td><td>{wk_coverage:.1f}%</td><td>{we_coverage:.1f}%</td><td class="{diff_class}">{diff:+.1f}%</td></tr>')
        
        html_lines.append('</table>')
    else:
        html_lines.append('<p>暂无数据</p>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    html_lines.append('</div>')
    
    html_lines.append('<div class="footer">通辽店 vs 松原一店 - 提成与覆盖率分析报告 | 自动生成于 ' + datetime.now().strftime('%Y-%m-%d %H:%M') + ' | 数据来源：糖果华庭 KTV</div>')
    html_lines.append('</div>')
    html_lines.append('</body>')
    html_lines.append('</html>')
    
    html_content = '\n'.join(html_lines)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f'✅ 分析报告(HTML)已生成: {output_path}')
    
    pdf_path = convert_html_to_pdf(output_path)
    if pdf_path:
        print(f'✅ PDF报告已生成: {pdf_path}')
    
    return output_path


def main():
    days = 30
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    
    start_date, end_date = get_date_range(days)
    print(f'📅 分析周期: {start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")}')
    
    # 获取提成数据
    print('📊 获取人员提成数据...')
    tongliao_commission_df = get_commission_data(STORE_IDS['通辽'], start_date, end_date)
    songyuan_commission_df = get_commission_data(STORE_IDS['松原一'], start_date, end_date)
    
    tongliao_commission = analyze_commission(tongliao_commission_df, '通辽店')
    songyuan_commission = analyze_commission(songyuan_commission_df, '松原一店')
    
    # 获取商品覆盖率数据
    print('� 获取商品销售覆盖率数据...')
    tongliao_coverage_df = get_product_coverage_data(STORE_IDS['通辽'], start_date, end_date)
    songyuan_coverage_df = get_product_coverage_data(STORE_IDS['松原一'], start_date, end_date)
    
    tongliao_coverage = analyze_product_coverage(tongliao_coverage_df, '通辽店', start_date, end_date)
    songyuan_coverage = analyze_product_coverage(songyuan_coverage_df, '松原一店', start_date, end_date)
    
    # 生成报告
    print('📝 生成分析报告...')
    output_path = generate_html_report(start_date, end_date, tongliao_commission, songyuan_commission,
                                       tongliao_coverage, songyuan_coverage)
    
    print('✅ 分析完成！')


if __name__ == "__main__":
    main()
