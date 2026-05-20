
#!/usr/bin/env python3
"""
检查39.9团购单价显示为69.8的问题 - 修正版
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
import pandas as pd

print("=" * 80)
print("检查团购数据 - 39.9套餐单价异常")
print("=" * 80)

# 先查看表结构
print("\n【0】查看order_detail和product_sales_detail的表结构")

sql_cols_od = "SHOW COLUMNS FROM order_detail"
df_cols_od = query(sql_cols_od)
print(f"\norder_detail 列: {df_cols_od['Field'].tolist()}")

sql_cols_psd = "SHOW COLUMNS FROM product_sales_detail"
df_cols_psd = query(sql_cols_psd)
print(f"product_sales_detail 列: {df_cols_psd['Field'].tolist()}")

# 查询最近的团购订单数据
print("\n" + "=" * 60)
print("【1】查询团购订单的实际金额")
print("=" * 60)

sql = """
SELECT 
    od.store_id,
    s.store_name,
    od.data_date,
    LEFT(od.order_no, 20) as order_no_short,
    od.source_channel,
    od.actual_amount,
    od.should_amount,
    od.order_type,
    od.room_no
FROM order_detail od
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-10'
    AND od.source_channel IN ('抖音', '美团大众', '线下团购')
ORDER BY od.actual_amount DESC
LIMIT 50
"""

df = query(sql)

if not df.empty:
    print(f"\n共 {len(df)} 条记录\n")
    
    for _, row in df.head(20).iterrows():
        print(f"{row['store_name']:8} | {row['source_channel']:6} | 实际:{row['actual_amount']:7.1f}元 | 应收:{row['should_amount']:.1f}元 | {row['room_no']}")

# 统计每个来源的平均价格
print("\n" + "=" * 60)
print("【2】按门店+来源统计平均价格")
print("=" * 60)

sql_stats = """
SELECT 
    s.store_name,
    od.source_channel,
    COUNT(*) as 订单数,
    ROUND(AVG(od.actual_amount), 2) as 平均单价,
    ROUND(MIN(od.actual_amount), 2) as 最低价,
    ROUND(MAX(od.actual_amount), 2) as 最高价,
    SUM(od.actual_amount) as 总销售额
FROM order_detail od
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-10'
    AND od.source_channel IN ('抖音', '美团大众', '线下团购')
GROUP BY s.store_name, od.source_channel
ORDER BY 总销售额 DESC
"""

df_stats = query(sql_stats)

for _, row in df_stats.iterrows():
    print(f"{row['store_name']:8} | {row['source_channel']:6} | 订单数:{row['订单数']:4} | 平均:{row['平均单价']:7.2f}元 | 范围:{row['最低价']:.0f}-{row['最高价']:.0f}")

# 查看套餐信息
print("\n" + "=" * 60)
print("【3】查看套餐名称与实际金额的关系")
print("=" * 60)

sql_pkg = """
SELECT 
    s.store_name,
    psd.package,
    COUNT(*) as 记录数,
    ROUND(SUM(psd.sales_amount), 2) as 销售总额
FROM product_sales_detail psd
JOIN stores s ON psd.store_id = s.id
WHERE psd.data_date = '2026-05-10'
    AND (psd.package LIKE '%39.9%' OR psd.package LIKE '%团购%')
GROUP BY s.store_name, psd.package
ORDER BY 销售总额 DESC
LIMIT 30
"""

df_pkg = query(sql_pkg)

if not df_pkg.empty:
    for _, row in df_pkg.iterrows():
        print(f"{row['store_name']:8} | 套餐: {row['package'][:40]:40} | 记录数:{row['记录数']:4} | 销售额:{row['销售总额']:.0f}")
else:
    print("没有找到包含'39.9'或'团购'的套餐记录")

# 直接查看所有套餐名
print("\n" + "=" * 60)
print("【4】查看2026-05-10的所有套餐名称（去重）")
print("=" * 60)

sql_all_pkgs = """
SELECT DISTINCT package, COUNT(*) as cnt
FROM product_sales_detail
WHERE data_date = '2026-05-10'
    AND package IS NOT NULL AND package != ''
GROUP BY package
ORDER BY cnt DESC
LIMIT 30
"""

df_all_pkgs = query(sql_all_pkgs)

for _, row in df_all_pkgs.iterrows():
    if '39.9' in str(row['package']) or '团购' in str(row['package']):
        print(f"★ {row['package'][:50]:50} ({row['cnt']}条)")
    else:
        print(f"  {row['package'][:50]:50} ({row['cnt']}条)")
