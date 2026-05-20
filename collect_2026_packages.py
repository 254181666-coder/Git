
#!/usr/bin/env python3
"""
收集2026年所有套餐信息
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("收集2026年5月所有套餐信息")
print("=" * 80)

# 查询所有团购套餐数据
sql = """
SELECT 
    psd.*,
    s.store_name
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date &gt;= '2026-05-01' AND psd.data_date &lt;= '2026-05-12'
    AND (psd.package LIKE '%%团购%%' OR psd.package LIKE '%%套餐%%')
ORDER BY s.store_name, psd.package, psd.data_date
"""

df = query(sql)

if not df.empty:
    print(f"共 {len(df)} 条记录")
    print(f"\n门店数量: {df['store_name'].nunique()}")
    print(f"套餐数量: {df['package'].nunique()}")
    
    # 保存详细数据
    df.to_csv(PROJECT_ROOT / 'data' / '2026_packages_detail.csv', index=False, encoding='utf-8-sig')
    print(f"详细数据已保存至: data/2026_packages_detail.csv")
    
    # 简单分析
    print("\n" + "=" * 80)
    print("套餐统计")
    print("=" * 80)
    
    pkg_stats = df.groupby(['store_name', 'package']).agg(
        商品种类=('product_name', 'nunique'),
        总记录数=('id', 'count')
    ).reset_index()
    
    print(f"\n共 {len(pkg_stats)} 个套餐\n")
    print(pkg_stats.head(20).to_string(index=False))

else:
    print("没有找到数据")
