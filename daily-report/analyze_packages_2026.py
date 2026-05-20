
#!/usr/bin/env python3
"""
收集2026年套餐数据并生成报告
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from datetime import datetime

print("=" * 80)
print("收集2026年5月套餐数据")
print("=" * 80)

# 使用简单的SQL先获取数据
df_all = query("""
SELECT psd.*, s.store_name
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-08'
ORDER BY s.store_name, psd.package
LIMIT 200
""")

# 然后用pandas过滤日期范围
if not df_all.empty:
    df = df_all[
        (df_all['data_date'] &gt;= '2026-05-01') &amp; 
        (df_all['data_date'] &lt;= '2026-05-11')
    ].copy()
else:
    df = pd.DataFrame()

if df.empty:
    print("没有找到数据")
    sys.exit()

# 进一步过滤包含套餐/团购的记录
df = df[df['package'].str.contains('套餐|团购', na=False)]

print(f"共 {len(df)} 条记录")
print(f"门店数量: {df['store_name'].nunique()}")
print(f"套餐数量: {df['package'].nunique()}")

# 分析每个套餐
all_packages = []

for (store_name, package_name), group in df.groupby(['store_name', 'package']):
    products = []
    for product_name, prod_group in group.groupby('product_name'):
        avg_qty = prod_group['quantity'].mean()
        total_amt = prod_group['sales_amount'].sum()
        total_qty = prod_group['quantity'].sum()
        avg_price = 0.0
        if total_qty &gt; 0:
            avg_price = total_amt / total_qty
        
        products.append({
            'name': product_name,
            'avg_qty': round(avg_qty, 2),
            'avg_price': round(avg_price, 2)
        })
    
    products.sort(key=lambda x: x['avg_qty'], reverse=True)
    
    all_packages.append({
        'store': store_name,
        'name': package_name,
        'products': products
    })

# 生成HTML报告
html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>2026年套餐详情报告</title>
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1400px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; margin-top: 30px 0 15px; border-left: 5px solid #3498db; padding-left: 10px; }
    h3 { color: #4a6fa5; margin: 20px 0 10px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 14px; }
    th, td { border: 1px solid #ddd; padding: 8px 10px; text-align: left; }
    th { background: #f0f8ff; font-weight: 600; }
    tr:nth-child(even) { background: #f9f9f9; }
    .footer { text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }
    .store-section { margin-bottom: 30px; padding: 15px; background: #fafafa; border-radius: 6px; }
</style>
</head>
<body>
    <div class="container">
        <h1>🎁 2026年5月套餐详情报告</h1>
        <div style="color: #7f8c8d; margin-bottom: 20px;">
"""

html += f"            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>"
html += "            数据范围: 2026年5月1日-11日"
html += """
        </div>
        
        <h2>📊 套餐概览</h2>
        <table>
            <tr><th>门店</th><th>套餐名称</th><th>商品种类</th></tr>
"""

for pkg in all_packages:
    html += f"""
        <tr>
            <td>{pkg['store']}</td>
            <td>{pkg['name']}</td>
            <td>{len(pkg['products'])}</td>
        </tr>
"""

html += """
        </table>
        <h2>📦 套餐详情</h2>
"""

current_store = ""
for pkg in all_packages:
    if pkg['store'] != current_store:
        if current_store:
            html += "        </div>"
        current_store = pkg['store']
        html += f"""
        <div class="store-section">
            <h3>🏪 {current_store}</h3>
"""
    
    html += f"""
            <h4>📋 {pkg['name']}</h4>
            <table>
                <tr><th>商品名称</th><th>平均数量</th><th>平均单价</th></tr>
"""
    
    for p in pkg['products']:
        html += f"""
                <tr>
                    <td>{p['name']}</td>
                    <td>{p['avg_qty']}</td>
                    <td>{p['avg_price']}</td>
                </tr>
"""
    
    html += "            </table>"

if current_store:
    html += "        </div>"

html += """
        <h2>📝 使用说明</h2>
        <p style="color: #666; line-height: 1.8;">
            以上是2026年5月1-11日的套餐数据。要完成与去年的对比分析，请：</p>
        <ul style="color: #666; margin-left: 20px; line-height: 2;">
            <li>提供您提到的两张去年套餐图片中的信息</li>
            <li>告诉我去年每个门店的套餐名称</li>
            <li>告诉我每个套餐包含的商品及数量</li>
            <li>我将生成详细的对比分析报告</li>
        </ul>
        <div class="footer">糖果华庭 KTV - 套餐分析报告</div>
    </div>
</body>
</html>
"""

# 保存报告
output_file = PROJECT_ROOT / 'data' / 'output' / 'packages_2026_report.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ 报告已生成: {output_file}")

# 也保存CSV数据
csv_file = PROJECT_ROOT / 'data' / 'packages_2026_raw.csv'
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"✅ 原始数据已保存: {csv_file}")

# 显示摘要
print("\n" + "=" * 80)
print("套餐摘要")
print("=" * 80)
for pkg in all_packages[:10]:
    print(f"\n【{pkg['store']} - {pkg['name']}】")
    for p in pkg['products'][:5]:
        print(f"  - {p['name']}: {p['avg_qty']}份 @ {p['avg_price']}元")
