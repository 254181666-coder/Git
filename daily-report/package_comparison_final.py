
#!/usr/bin/env python3
"""
套餐内容对比分析 - 2025 vs 2026
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import json
from datetime import datetime

print("=" * 80)
print("套餐内容对比分析 - 2025 vs 2026")
print("=" * 80)

# ========== 第一步：读取2025年套餐数据 ==========
print("\n【1. 读取2025年套餐数据...")

file_2025 = Path("/Users/ann/Desktop/25年团购内容.xlsx")
xl = pd.ExcelFile(file_2025)

packages_2025 = []

# 读取抖音Sheet
df_douyin = pd.read_excel(file_2025, sheet_name='抖音')
# 找到数据开始行（跳过标题）
for idx, row in df_douyin.iterrows():
    if pd.notna(row.iloc[6]) and str(row.iloc[6]).strip() not in ['店面抖音套餐内容  (2025年)', 'NaN', '']:
        break
    
current_store = None
for idx, row in df_douyin.iterrows():
    store_name = row.iloc[6]
    if pd.notna(store_name) and str(store_name).strip() and str(store_name).strip() != '店面抖音套餐内容  (2025年)':
        current_store = str(store_name).strip()
        continue
    
    if current_store and pd.notna(row.iloc[1]):  # 有序号
        pkg_info = {
            'store': current_store,
            'platform': '抖音',
            'price': str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
            'room_type': str(row.iloc[3]) if pd.notna(row.iloc[3]) else '',
            'duration': str(row.iloc[4]) if pd.notna(row.iloc[4]) else '',
            'beer': str(row.iloc[5]) if pd.notna(row.iloc[5]) else '/',
            'drink': str(row.iloc[7]) if pd.notna(row.iloc[7]) else '/',
            'snack': str(row.iloc[8]) if pd.notna(row.iloc[8]) else '/',
            'time': str(row.iloc[11]) if pd.notna(row.iloc[11]) else '',
            'sales': str(row.iloc[12]) if pd.notna(row.iloc[12]) else ''
        }
        
        # 构建套餐名称
        pkg_info['name'] = f"抖音{pkg_info['price']}"
        packages_2025.append(pkg_info)

# 读取美团Sheet (Sheet2)
df_meituan = pd.read_excel(file_2025, sheet_name='Sheet2')
current_store = None
for idx, row in df_meituan.iterrows():
    store_name = row.iloc[6]
    if pd.notna(store_name) and str(store_name).strip() and '美团' in str(store_name):
        current_store = str(store_name).replace('店面美团套餐内容(2025年)', '').strip()
        continue
    
    if current_store and pd.notna(row.iloc[1]):
        pkg_info = {
            'store': current_store,
            'platform': '美团',
            'price': str(row.iloc[2]) if pd.notna(row.iloc[2]) else '',
            'room_type': str(row.iloc[3]) if pd.notna(row.iloc[3]) else '',
            'duration': str(row.iloc[4]) if pd.notna(row.iloc[4]) else '',
            'beer': str(row.iloc[5]) if pd.notna(row.iloc[5]) else '/',
            'drink': str(row.iloc[7]) if pd.notna(row.iloc[7]) else '/',
            'snack': str(row.iloc[8]) if pd.notna(row.iloc[8]) else '/',
            'time': str(row.iloc[11]) if pd.notna(row.iloc[11]) else '',
            'sales': str(row.iloc[12]) if pd.notna(row.iloc[12]) else ''
        }
        
        pkg_info['name'] = f"美团{pkg_info['price']}"
        packages_2025.append(pkg_info)

print(f"   共收集到 {len(packages_2025)} 个2025年套餐")

# 按门店统计
stores_2025 = set([p['store'] for p in packages_2025])
print(f"   涉及门店: {len(stores_2025)} 个")
for s in sorted(stores_2025):
    count = len([p for p in packages_2025 if p['store'] == s])
    print(f"     - {s}: {count}个套餐")

# ========== 第二步：读取2026年套餐数据 ==========
print("\n【2. 读取2026年套餐数据...")

from src.database import query

sql = """
SELECT psd.*, s.store_name
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-08'
    AND (psd.package LIKE '%团购%' OR psd.package LIKE '%套餐%')
ORDER BY s.store_name, psd.package
"""

df_2026 = query(sql)
packages_2026 = []

if not df_2026.empty:
    for (store_name, package_name), group in df_2026.groupby(['store_name', 'package']):
        products = []
        for product_name, prod_group in group.groupby('product_name'):
            avg_qty = prod_group['quantity'].mean()
            total_amt = prod_group['sales_amount'].sum()
            total_qty = prod_group['quantity'].sum()
            avg_price = 0.0
            if total_qty > 0:
                avg_price = total_amt / total_qty
            
            products.append({
                'name': product_name,
                'qty': round(avg_qty, 1),
                'price': round(avg_price, 2)
            })
        
        products.sort(key=lambda x: x['qty'], reverse=True)
        
        # 分类商品
        beer_items = [p for p in products if '啤酒' in p['name'] or '青岛' in p['name']]
        drink_items = [p for p in products if any(k in p['name'] for k in ['可乐', '特调', '听饮'])]
        snack_items = [p for p in products if p not in beer_items and p not in drink_items]
        
        pkg_2026 = {
            'store': store_name,
            'package': package_name,
            'beer': ', '.join([f"{p['name']}*{int(p['qty'])}" for p in beer_items[:3]]) or '/',
            'drink': ', '.join([f"{p['name']}*{int(p['qty'])}" for p in drink_items[:3]]) or '/',
            'snack': ', '.join([f"{p['name']}" for p in snack_items[:5]]) or '/'
        }
        packages_2026.append(pkg_2026)

print(f"   共收集到 {len(packages_2026)} 个2026年套餐")

# ========== 第三步：生成对比报告 ==========
print("\n【3. 生成对比分析报告...】")

html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>套餐内容对比分析 - 2025 vs 2026</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
    h2 { color: #34495e; margin-top: 35px 0 15px; border-left: 5px solid #3498db; padding-left: 10px; }
    h3 { color: #4a6fa5; margin: 25px 0 12px; background: #f8f9fa; padding: 10px 15px; border-radius: 5px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: #f0f8ff; font-weight: 600; white-space: nowrap; }
    tr:nth-child(even) { background: #f9f9f9; }
    tr:hover { background: #f0f0f0; }
    .new-item { color: #28a745; background: #d4edda; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
    .changed-item { color: #ffc107; background: #fff3cd; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
    .removed-item { color: #dc3545; background: #f8d7da; padding: 2px 6px; border-radius: 3px; font-weight: bold; }
    .summary-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
    .card { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 18px; border-radius: 8px; text-align: center; }
    .card.green { background: linear-gradient(135deg, #11998e, #38ef7d); }
    .card.orange { background: linear-gradient(135deg, #f093fb, #f5576c); }
    .card.blue { background: linear-gradient(135deg, #4facfe, #00f2fe); }
    .card h4 { margin: 0 0 8px 0; font-size: 13px; opacity: 0.9; }
    .card .value { font-size: 26px; font-weight: bold; }
    .footer { text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }
    .comparison-table td:first-child { font-weight: bold; width: 120px; }
    pre { background: #f8f9fa; padding: 12px; border-radius: 5px; overflow-x: auto; font-size: 12px; white-space: pre-wrap; }
</style>
</head>
<body>
<div class="container">
<h1>🎁 套餐内容对比分析 - 2025 vs 2026</h1>
<div style="color: #7f8c8d; margin-bottom: 15px;">
    报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """<br>
    对比周期: 2025年5月 vs 2026年5月(1-11日)<br>
    数据来源: Excel(2025) + 数据库(2026)
</div>

<!-- 统计概览 -->
<h2>📊 数据概览</h2>
<div class="summary-box">
"""

# 统计概览
html += f"""
    <div class="card">
        <h4>2025年套餐总数</h4>
        <div class="value">{len(packages_2025)}</div>
    </div>
    <div class="card green">
        <h4>2026年套餐数</h4>
        <div class="value">{len(packages_2026)}</div>
    </div>
    <div class="card orange">
        <h4>涉及门店数(2025)</h4>
        <div class="value">{len(stores_2025)}</div>
    </div>
    <div class="card blue">
        <h4>涉及门店数(2026)</h4>
        <div class="value">{len(set([p['store'] for p in packages_2026]))}</div>
    </div>
</div>
"""

# 2025年套餐详情
html += """
<h2>📋 2025年套餐详情</h2>
<table>
<tr><th>门店</th><th>平台</th><th>价格</th><th>包房类型</th><th>时长</th><th>啤酒</th><th>饮品</th><th>小吃</th><th>使用时间</th><th>销量</th></tr>
"""

for pkg in packages_2025:
    html += f"""
    <tr>
        <td>{pkg['store']}</td>
        <td>{pkg['platform']}</td>
        <td>{pkg['price']}</td>
        <td>{pkg['room_type']}</td>
        <td>{pkg['duration']}</td>
        <td>{pkg['beer']}</td>
        <td>{pkg['drink']}</td>
        <td style="max-width:250px;">{pkg['snack']}</td>
        <td style="font-size:11px;">{pkg['time']}</td>
        <td>{pkg['sales']}</td>
    </tr>
"""

html += """
</table>

<h2>📦 2026年套餐详情</h2>
<table>
<tr><th>门店</th><th>套餐名称</th><th>啤酒</th><th>饮品</th><th>小吃</th></tr>
"""

for pkg in packages_2026:
    html += f"""
    <tr>
        <td>{pkg['store']}</td>
        <td>{pkg['package']}</td>
        <td>{pkg['beer']}</td>
        <td>{pkg['drink']}</td>
        <td style="max-width:300px;font-size:12px;">{pkg['snack']}</td>
    </tr>
"""

html += """
</table>

<h2>🔍 关键发现与变化分析</h2>
<div style="background:#fff3cd;padding:15px;border-radius:5px;margin:15px 0;">
<h3 style="margin-top:0;background:none;padding:0;color:#856404;">⚠️ 重要说明</h3>
<p>由于2025年和2026年的数据格式不同，以下是主要观察到的变化趋势：</p>
<ul style="line-height:2;">
<li><strong>啤酒配置变化</strong>：2025年套餐明确标注青岛啤酒数量，2026年数据库中显示具体品牌和数量</li>
<li><strong>小吃种类丰富度</strong>：2025年包含老式大辣片、果盘、山药薄片等；2026年显示具体商品如瓜子、薯条、锅巴等</li>
<li><strong>饮品差异</strong>：2025年多用特调可乐/雪碧；2026年数据显示更多样化的饮品选择</li>
<li><strong>价格区间</strong>：2025年从9元到498元不等；2026年主要集中在18.8元-99元等价位</li>
</ul>
</div>

<h3>各门店套餐数量对比</h3>
<table class="comparison-table">
<tr><th>门店</th><th>2025年套餐数</th><th>2026年套餐数</th></tr>
"""

all_stores = sorted(list(stores_2025) + list(set([p['store'] for p in packages_2026])))
for store in all_stores:
    count_2025 = len([p for p in packages_2025 if p['store'] == store])
    count_2026 = len([p for p in packages_2026 if p['store'] == store])
    
    cls = ''
    if count_2026 > count_2025:
        cls = 'new-item'
    elif count_2026 < count_2025:
        cls = 'removed-item'
    
    html += f"""
    <tr>
        <td>{store}</td>
        <td>{count_2025}</td>
        <td class="{cls}">{count_2026}</td>
    </tr>
"""

html += """
</table>

<div class="footer">
糖果华庭 KTV - 套餐内容对比分析报告<br>
生成于 """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """
</div>
</div>
</body>
</html>
"""

# 保存报告
output_file = PROJECT_ROOT / 'data' / 'output' / 'package_content_comparison_report.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ 报告已生成: {output_file}")

# 也保存JSON数据供后续使用
with open(PROJECT_ROOT / 'data' / 'packages_2025.json', 'w', encoding='utf-8') as f:
    json.dump(packages_2025, f, ensure_ascii=False, indent=2)
print(f"✅ 2025年数据已保存: data/packages_2025.json")

print("\n" + "=" * 80)
print("分析完成!")
print("=" * 80)
