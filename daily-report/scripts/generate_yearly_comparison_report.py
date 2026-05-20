#!/usr/bin/env python3
"""
年度同比对比分析报告生成脚本
生成当前日期与2025年同期数据的对比报告
专注于各门店同比分析
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from src.database import query
from src.config import OUTPUT_DIR

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 门店名称映射
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

def unify_store_name(name):
    if not name:
        return None
    name = str(name).strip()
    if name in STORE_NAME_MERGE:
        return STORE_NAME_MERGE[name]
    return name

def get_store_data(date_str):
    """获取指定日期的门店数据"""
    sql = """
        SELECT 
            s.store_name,
            sd.total_revenue,
            sd.stored_card_sales,
            sd.online_groupbuy,
            sd.customers_before_18,
            sd.customers_18_to_24,
            sd.customers_after_00
        FROM store_daily sd
        JOIN stores s ON sd.store_id = s.id
        WHERE sd.data_date = %s
    """
    df = query(sql, (date_str,))
    if not df.empty:
        df['门店'] = df['store_name'].apply(unify_store_name)
        df = df[df['门店'].notna()]
    return df

def prepare_comparison_data(current_date, last_year_date):
    """准备同比对比数据"""
    df_current = get_store_data(current_date)
    df_last = get_store_data(last_year_date)
    
    if df_current.empty and df_last.empty:
        return None
    
    # 定义所有需要的列
    current_cols = ['门店', '总营收_本期', '储值卡营收_本期', '团购营收_本期', 
                    '日场待客_本期', '晚场待客_本期', '午夜场待客_本期']
    last_cols = ['门店', '总营收_去年', '储值卡营收_去年', '团购营收_去年', 
                 '日场待客_去年', '晚场待客_去年', '午夜场待客_去年']
    
    # 准备本期数据
    if not df_current.empty:
        current_data = df_current.rename(columns={
            'total_revenue': '总营收_本期',
            'stored_card_sales': '储值卡营收_本期',
            'online_groupbuy': '团购营收_本期',
            'customers_before_18': '日场待客_本期',
            'customers_18_to_24': '晚场待客_本期',
            'customers_after_00': '午夜场待客_本期'
        })[current_cols].copy()
    else:
        current_data = pd.DataFrame(columns=current_cols)
    
    # 准备去年数据
    if not df_last.empty:
        last_data = df_last.rename(columns={
            'total_revenue': '总营收_去年',
            'stored_card_sales': '储值卡营收_去年',
            'online_groupbuy': '团购营收_去年',
            'customers_before_18': '日场待客_去年',
            'customers_18_to_24': '晚场待客_去年',
            'customers_after_00': '午夜场待客_去年'
        })[last_cols].copy()
    else:
        last_data = pd.DataFrame(columns=last_cols)
    
    # 合并数据
    merged = current_data.merge(last_data, on='门店', how='outer')
    merged = merged.fillna(0)
    
    # 确保所有列都存在，缺失的用0填充
    for col in current_cols + last_cols:
        if col not in merged.columns:
            merged[col] = 0
    
    # 计算总可待客
    merged['总可待客_本期'] = merged['日场待客_本期'] + merged['晚场待客_本期'] + merged['午夜场待客_本期']
    merged['总可待客_去年'] = merged['日场待客_去年'] + merged['晚场待客_去年'] + merged['午夜场待客_去年']
    
    # 计算增长量和增长率
    for col in ['总营收', '储值卡营收', '团购营收', '日场待客', '晚场待客', '午夜场待客', '总可待客']:
        merged[f'{col}_增量'] = merged[f'{col}_本期'] - merged[f'{col}_去年']
        merged[f'{col}_增长率'] = merged.apply(
            lambda x: (x[f'{col}_增量'] / x[f'{col}_去年'] * 100) if x[f'{col}_去年'] > 0 else 0,
            axis=1
        )
    
    return merged

def generate_comparison_chart(data, target_date):
    """生成同比对比图表"""
    CHART_FILE = f'{OUTPUT_DIR}/同比对比分析图_{target_date}.png'
    
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle(f'各门店年度同比对比分析 - {target_date}', fontsize=18, fontweight='bold')
    
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.35)
    
    # 1. 各门店总营收对比（横向柱状图）
    ax1 = fig.add_subplot(gs[0, 0])
    data_sorted = data.sort_values('总营收_本期', ascending=True)
    y = range(len(data_sorted))
    height = 0.35
    
    bars1a = ax1.barh([yi - height/2 for yi in y], data_sorted['总营收_本期']/10, height, label='本期', color='#3498db')
    bars1b = ax1.barh([yi + height/2 for yi in y], data_sorted['总营收_去年']/10, height, label='2025年同期', color='#e74c3c')
    
    # 添加数值标签
    for bar in bars1a:
        width = bar.get_width()
        ax1.text(width + 2, bar.get_y() + bar.get_height()/2, 
                f'{width:,.0f}', va='center', ha='left', fontsize=8, color='black')
    for bar in bars1b:
        width = bar.get_width()
        ax1.text(width + 2, bar.get_y() + bar.get_height()/2, 
                f'{width:,.0f}', va='center', ha='left', fontsize=8, color='black')
    
    ax1.set_yticks(y)
    ax1.set_yticklabels(data_sorted['门店'], fontsize=10)
    ax1.set_xlabel('营收 (元)', fontsize=11)
    ax1.set_title('各门店总营收对比', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='x')
    
    # 2. 各门店总营收增长率（横向柱状图）
    ax2 = fig.add_subplot(gs[0, 1])
    growth_sorted = data.sort_values('总营收_增长率', ascending=True)
    colors = ['#28a745' if x >= 0 else '#dc3545' for x in growth_sorted['总营收_增长率']]
    
    bars2 = ax2.barh(range(len(growth_sorted)), growth_sorted['总营收_增长率'], color=colors)
    
    # 添加数值标签
    for i, bar in enumerate(bars2):
        width = bar.get_width()
        if width >= 0:
            ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{width:+.1f}%', va='center', ha='left', fontsize=8, color='black')
        else:
            ax2.text(width - 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{width:+.1f}%', va='center', ha='right', fontsize=8, color='black')
    
    ax2.set_yticks(range(len(growth_sorted)))
    ax2.set_yticklabels(growth_sorted['门店'], fontsize=10)
    ax2.set_xlabel('增长率 (%)', fontsize=11)
    ax2.set_title('各门店总营收同比增长率', fontsize=13, fontweight='bold')
    ax2.axvline(x=0, color='#333', linestyle='-', linewidth=0.5)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # 3. 各门店待客量对比
    ax3 = fig.add_subplot(gs[1, 0])
    data_sorted2 = data.sort_values('总可待客_本期', ascending=True)
    
    bars3a = ax3.barh([yi - height/2 for yi in range(len(data_sorted2))], data_sorted2['总可待客_本期'], height, label='本期', color='#28a745')
    bars3b = ax3.barh([yi + height/2 for yi in range(len(data_sorted2))], data_sorted2['总可待客_去年'], height, label='2025年同期', color='#ffc107')
    
    # 添加数值标签
    for bar in bars3a:
        width = bar.get_width()
        ax3.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{int(width)}', va='center', ha='left', fontsize=8, color='black')
    for bar in bars3b:
        width = bar.get_width()
        ax3.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{int(width)}', va='center', ha='left', fontsize=8, color='black')
    
    ax3.set_yticks(range(len(data_sorted2)))
    ax3.set_yticklabels(data_sorted2['门店'], fontsize=10)
    ax3.set_xlabel('待客人数', fontsize=11)
    ax3.set_title('各门店总可待客对比', fontsize=13, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='x')
    
    # 4. 各门店储值卡营收对比
    ax4 = fig.add_subplot(gs[1, 1])
    data_sorted3 = data.sort_values('储值卡营收_本期', ascending=True)
    
    bars4a = ax4.barh([yi - height/2 for yi in range(len(data_sorted3))], data_sorted3['储值卡营收_本期']/10, height, label='本期', color='#6610f2')
    bars4b = ax4.barh([yi + height/2 for yi in range(len(data_sorted3))], data_sorted3['储值卡营收_去年']/10, height, label='2025年同期', color='#fd7e14')
    
    # 添加数值标签
    for bar in bars4a:
        width = bar.get_width()
        ax4.text(width + 2, bar.get_y() + bar.get_height()/2, 
                f'{width:,.0f}', va='center', ha='left', fontsize=8, color='black')
    for bar in bars4b:
        width = bar.get_width()
        ax4.text(width + 2, bar.get_y() + bar.get_height()/2, 
                f'{width:,.0f}', va='center', ha='left', fontsize=8, color='black')
    
    ax4.set_yticks(range(len(data_sorted3)))
    ax4.set_yticklabels(data_sorted3['门店'], fontsize=10)
    ax4.set_xlabel('储值卡营收 (元)', fontsize=11)
    ax4.set_title('各门店储值卡营收对比', fontsize=13, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig(CHART_FILE, dpi=150, facecolor='white')
    plt.close()
    
    clear_extended_attributes(CHART_FILE)
    print(f"✅ 同比对比分析图已保存: {CHART_FILE}")
    return CHART_FILE

def clear_extended_attributes(file_path):
    """清除文件的扩展属性"""
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

def generate_html_report(target_date, data, chart_path):
    """生成HTML报告"""
    last_year_date = target_date.replace('2026', '2025')
    output_path = OUTPUT_DIR / f'同比对比分析报告_{target_date}.html'
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>各门店年度同比对比报告 - {target_date}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;line-height:1.6;color:#333;background:#f5f5f5}}
.container{{max-width:1600px;margin:0 auto;background:white;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
h1{{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:30px;font-size:28px}}
h2{{color:#34495e;margin:30px 0 15px;border-left:5px solid #3498db;padding-left:10px;font-size:20px}}
table{{width:100%;border-collapse:collapse;margin:15px 0;background:white;font-size:13px}}
th,td{{border:1px solid #ddd;padding:8px 10px;text-align:center}}
th{{background:#f0f8ff;font-weight:600}}
tr:nth-child(even){{background:#f9f9f9}}
tr:hover{{background:#f5f5f5}}
.positive{{color:#28a745;font-weight:bold}}
.negative{{color:#dc3545;font-weight:bold}}
.footer{{text-align:center;color:#999;font-size:14px;margin-top:40px;padding-top:20px;border-top:1px solid #eee}}
.section{{margin-bottom:40px;padding-bottom:20px;border-bottom:2px solid #eee}}
.section:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.chart-container{{text-align:center;margin:20px 0}}
.chart-container img{{max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
</style>
</head>
<body>
<div class="container">
<h1>各门店年度同比对比报告</h1>
<div style="color:#7f8c8d;margin-bottom:20px;">
  <strong>本期日期:</strong> {target_date} | <strong>对比日期:</strong> {last_year_date}
</div>

<div class="section">
<h2>一、可视化分析</h2>
<div class="chart-container">
<img src="同比对比分析图_{target_date}.png" alt="同比对比分析图">
</div>
</div>

<div class="section">
<h2>二、各门店详细数据对比</h2>
<table>
<tr><th rowspan="2">门店</th><th colspan="3">总营收 (元)</th><th colspan="3">储值卡营收 (元)</th><th colspan="3">团购营收 (元)</th></tr>
<tr><th>本期</th><th>去年同期</th><th>增长率</th><th>本期</th><th>去年同期</th><th>增长率</th><th>本期</th><th>去年同期</th><th>增长率</th></tr>
'''
    
    for _, row in data.iterrows():
        growth_rev = row['总营收_增长率']
        growth_card = row['储值卡营收_增长率']
        growth_tuan = row['团购营收_增长率']
        
        html_content += f'''<tr>
<td><strong>{row['门店']}</strong></td>
<td class="positive">{row['总营收_本期']/10:,.0f}</td>
<td>{row['总营收_去年']/10:,.0f}</td>
<td{" class='positive'" if growth_rev >= 0 else " class='negative'"}>{growth_rev:+.1f}%</td>
<td class="positive">{row['储值卡营收_本期']/10:,.0f}</td>
<td>{row['储值卡营收_去年']/10:,.0f}</td>
<td{" class='positive'" if growth_card >= 0 else " class='negative'"}>{growth_card:+.1f}%</td>
<td class="positive">{row['团购营收_本期']/10:,.0f}</td>
<td>{row['团购营收_去年']/10:,.0f}</td>
<td{" class='positive'" if growth_tuan >= 0 else " class='negative'"}>{growth_tuan:+.1f}%</td>
</tr>
'''
    
    html_content += '''</table>
</div>

<div class="section">
<h2>三、各门店待客量对比</h2>
<table>
<tr><th rowspan="2">门店</th><th colspan="3">总可待客 (人)</th><th colspan="3">日场待客 (人)</th><th colspan="3">晚场待客 (人)</th><th colspan="3">午夜场待客 (人)</th></tr>
<tr><th>本期</th><th>去年同期</th><th>增长率</th><th>本期</th><th>去年同期</th><th>增长率</th><th>本期</th><th>去年同期</th><th>增长率</th><th>本期</th><th>去年同期</th><th>增长率</th></tr>
'''
    
    for _, row in data.iterrows():
        growth_total = row['总可待客_增长率']
        growth_day = row['日场待客_增长率']
        growth_evening = row['晚场待客_增长率']
        growth_night = row['午夜场待客_增长率']
        
        html_content += f'''<tr>
<td><strong>{row['门店']}</strong></td>
<td class="positive">{int(row['总可待客_本期']):,}</td>
<td>{int(row['总可待客_去年']):,}</td>
<td{" class='positive'" if growth_total >= 0 else " class='negative'"}>{growth_total:+.1f}%</td>
<td class="positive">{int(row['日场待客_本期']):,}</td>
<td>{int(row['日场待客_去年']):,}</td>
<td{" class='positive'" if growth_day >= 0 else " class='negative'"}>{growth_day:+.1f}%</td>
<td class="positive">{int(row['晚场待客_本期']):,}</td>
<td>{int(row['晚场待客_去年']):,}</td>
<td{" class='positive'" if growth_evening >= 0 else " class='negative'"}>{growth_evening:+.1f}%</td>
<td class="positive">{int(row['午夜场待客_本期']):,}</td>
<td>{int(row['午夜场待客_去年']):,}</td>
<td{" class='positive'" if growth_night >= 0 else " class='negative'"}>{growth_night:+.1f}%</td>
</tr>
'''
    
    html_content += f'''</table>
</div>

<div class="footer">各门店年度同比对比报告 | 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据来源：糖果华庭 KTV 各门店</div>
</div>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    clear_extended_attributes(output_path)
    print(f"✅ 同比对比分析报告(HTML)已生成: {output_path}")
    return output_path

def convert_html_to_pdf(html_path):
    """使用Chrome headless模式将HTML转换为PDF - 优化版"""
    import time
    import subprocess
    
    pdf_dir = PROJECT_ROOT / 'data' / 'output_pdf'
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_name = html_path.stem + '.pdf'
    pdf_path = pdf_dir / pdf_name
    
    # 如果旧PDF存在，先删除
    if pdf_path.exists():
        try:
            pdf_path.unlink()
            time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ 删除旧PDF失败: {e}")
    
    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
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
        cmd = [
            chrome_path,
            '--headless=new',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-software-rasterizer',
            '--disable-features=VizDisplayCompositor',
            f'--print-to-pdf={pdf_path.absolute()}',
            '--no-margins',
            '--disable-dev-shm-usage',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=10000',
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

def main():
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    
    last_year_date = target_date.replace('2026', '2025')
    print(f"📅 生成各门店同比对比报告: {target_date} vs {last_year_date}")
    
    # 获取数据
    data = prepare_comparison_data(target_date, last_year_date)
    
    if data is None or data.empty:
        print("❌ 没有数据可用")
        return False
    
    print(f"   门店数: {len(data)}")
    
    # 生成图表
    chart_path = generate_comparison_chart(data, target_date)
    
    # 生成HTML报告
    html_path = generate_html_report(target_date, data, chart_path)
    
    # 转换PDF
    pdf_path = convert_html_to_pdf(html_path)
    
    if pdf_path:
        print(f"✅ 各门店同比对比报告生成完成")
        return True
    
    return False

if __name__ == '__main__':
    main()
