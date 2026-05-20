
#!/usr/bin/env python3
"""
套餐对比分析 - 2025 vs 2026
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd
from datetime import datetime

print("=" * 80)
print("套餐对比分析 - 2025 vs 2026")
print("=" * 80)

# ========== 第一步：收集2026年套餐数据
print("\n【1. 收集2026年套餐数据...")

sql_2026 = """
SELECT 
    psd.*,
    s.store_name
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date &gt;= '2026-05-01' AND psd.data_date &lt;= '2026-05-11'
    AND (psd.package LIKE '%%团购%%' OR psd.package LIKE '%%套餐%%')
ORDER BY s.store_name, psd.package
"""

df_2026 = query(sql_2026)

if not df_2026.empty:
    print(f"   共 {len(df_2026)} 条记录")
    
    # 分析2026年套餐
    pkg_2026 = []
    for (store_name, package_name), group in df_2026.groupby(['store_name', 'package']):
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
                'qty': round(avg_qty, 2),
                'price': round(avg_price, 2)
            })
        
        pkg_2026.append({
            'store': store_name,
            'name': package_name,
            'products': products
        })
    
    print(f"   2026年共 {len(pkg_2026)} 个套餐")

# ========== 第二步：定义2025年套餐数据（从您提供的图片中整理）
print("\n【2. 2025年套餐信息需要您提供...")

# 这里需要您补充去年的套餐数据
packages_2025 = [
    # 请根据您的图片内容补充去年的套餐
    # 示例格式：
    # {
    #     'store': '门店名称',
    #     'name': '套餐名称',
    #     'products': [
    #         {'name': '商品名称', 'qty': 数量, 'price': 单价},
    #         # ...
    #     ]
    # },
]

# ========== 第三步：对比分析
print("\n【3. 准备生成对比报告...")

html = f"""
&lt;!DOCTYPE html&gt;
&lt;html lang="zh-CN"&gt;
&lt;head&gt;
&lt;meta charset="UTF-8"&gt;
&lt;title&gt;套餐对比分析 - 2025 vs 2026&lt;/title&gt;
&lt;style&gt;
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
    .container {{ max-width: 1400px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
    h2 {{ color: #34495e; margin-top: 30px 0 15px; border-left: 5px solid #3498db; padding-left: 10px; }}
    h3 {{ color: #4a6fa5; margin: 20px 0 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; }}
    th {{ background: #f0f8ff; font-weight: 600; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .add {{ color: #28a745; background: #d4edda; }}
    .remove {{ color: #dc3545; background: #f8d7da; }}
    .change {{ color: #ffc107; background: #fff3cd; }}
    .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}
&lt;/style&gt;
&lt;/head&gt;
&lt;body&gt;
    &lt;div class="container"&gt;
        &lt;h1&gt;🎁 套餐对比分析 - 2025 vs 2026&lt;/h1&gt;
        &lt;div style="color: #7f8c8d; margin-bottom: 20px;"&gt;
            报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}&lt;br&gt;
            对比周期: 2025年5月1-11日 vs 2026年5月1-11日
        &lt;/div&gt;
"""

# 添加2026年套餐总结
html += """
        &lt;h2&gt;📊 2026年套餐概览&lt;/h2&gt;
        &lt;table&gt;
            &lt;tr&gt;&lt;th&gt;门店&lt;/th&gt;&lt;th&gt;套餐名称&lt;/th&gt;&lt;th&gt;商品种类&lt;/th&gt;&lt;th&gt;主要商品&lt;/th&gt;&lt;/tr&gt;
"""

if not df_2026.empty:
    pkg_summary = df_2026.groupby(['store_name', 'package']).agg(
        商品种类=('product_name', 'nunique'),
        主要商品=('product_name', lambda x: ', '.join(x.unique()[:5]))
    ).reset_index()
    
    for _, row in pkg_summary.iterrows():
        html += f"""
            &lt;tr&gt;
                &lt;td&gt;{row['store_name']}&lt;/td&gt;
                &lt;td&gt;{row['package']}&lt;/td&gt;
                &lt;td&gt;{row['商品种类']}&lt;/td&gt;
                &lt;td&gt;{row['主要商品']}&lt;/td&gt;
            &lt;/tr&gt;
        """

html += """
        &lt;/table&gt;
        &lt;h2&gt;📝 使用说明&lt;/h2&gt;
        &lt;p style="color: #666; line-height: 1.8;"&gt;
            请将去年的套餐信息已从您提供的两张图片中整理，需要您补充去年（或我帮您）：&lt;/p&gt;
        &lt;ul style="color: #666; margin-left: 20px; line-height: 2;"&gt;
            &lt;li&gt;将去年门店和去年的套餐名称&lt;/li&gt;
            &lt;li&gt;每个套餐包含的商品名称&lt;/li&gt;
            &lt;li&gt;每个商品的数量和价格&lt;/li&gt;
        &lt;/ul&gt;
        &lt;div class="footer"&gt;糖果华庭 KTV - 套餐对比分析报告&lt;/div&gt;
    &lt;/div&gt;
&lt;/body&gt;
&lt;/html&gt;
"""

# 保存报告
output_file = PROJECT_ROOT / 'data' / 'output' / 'package_comparison_report.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ 报告已生成: {output_file}")

# 显示一些2026年的套餐示例
if not df_2026.empty:
    print("\n" + "=" * 80)
    print("2026年套餐示例")
    print("=" * 80)
    
    sample_pkgs = df_2026.groupby(['store_name', 'package']).head(1)
    
    for _, row in sample_pkgs.head(10).iterrows():
        print(f"\n【{row['store_name']} - {row['package']}】")
        
        # 获取该套餐的所有商品
        pkg_items = df_2026[
            (df_2026['store_name'] == row['store_name']) &amp; 
            (df_2026['package'] == row['package'])
        ]
        
        products = pkg_items['product_name'].unique()
        for p_list = ', '.join(products[:10])
        print(f"   包含商品: {p_list}")
