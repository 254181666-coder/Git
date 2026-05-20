
#!/usr/bin/env python3
"""
检查团购月度报告中套餐包含的商品信息
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("检查套餐商品信息")
print("=" * 80)

# 查看product_sales_detail中团购相关的数据
sql = """
SELECT 
    s.store_name,
    psd.package,
    psd.product_name,
    SUM(psd.quantity) as 总数量,
    ROUND(SUM(psd.sales_amount), 2) as 销售额,
    COUNT(*) as 记录数
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-10'
    AND (psd.package LIKE '%39.9%' OR psd.package LIKE '%团购%')
    AND psd.product_name IS NOT NULL AND psd.product_name != ''
GROUP BY s.store_name, psd.package, psd.product_name
ORDER BY s.store_name, psd.package, 总数量 DESC
"""

df = query(sql)

if not df.empty:
    print(f"\n共 {len(df)} 条记录\n")
    
    # 按门店和套餐分组展示
    current_store = None
    current_pkg = None
    
    for _, row in df.iterrows():
        if row['store_name'] != current_store:
            current_store = row['store_name']
            current_pkg = None
            print(f"\n{'='*60}")
            print(f"【{current_store}】")
            print('='*60)
        
        if row['package'] != current_pkg:
            current_pkg = row['package']
            print(f"\n  📦 套餐: {current_pkg}")
            print("  ─────────────────────────────")
        
        print(f"     • {row['product_name']:30} | 数量:{row['总数量']:5} | 销售额: {row['销售额']:7.1f}")
else:
    print("没有找到数据")

# 统计每个套餐包含多少种商品
print("\n" + "=" * 80)
print("【统计】各套餐包含的商品种类数")
print("=" * 80)

sql_summary = """
SELECT 
    s.store_name,
    psd.package,
    COUNT(DISTINCT psd.product_name) as 商品种类数,
    GROUP_CONCAT(DISTINCT psd.product_name SEPARATOR '、') as 商品列表
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-10'
    AND (psd.package LIKE '%39.9%' OR psd.package LIKE '%团购%')
    AND psd.product_name IS NOT NULL AND psd.product_name != ''
GROUP BY s.store_name, psd.package
HAVING COUNT(DISTINCT psd.product_name) > 0
ORDER BY s.store_name, 商品种类数 DESC
"""

df_summary = query(sql_summary)

for _, row in df_summary.iterrows():
    print(f"\n【{row['store_name']}】{row['package'][:40]}")
    print(f"   包含 {row['商品种类数']} 种商品:")
    
    products = str(row['商品列表']).split('、')
    for p in products[:10]:  # 只显示前10个
        if p.strip():
            print(f"     - {p.strip()}")
    
    if len(products) > 10:
        print(f"     ... 还有 {len(products)-10} 种商品")
