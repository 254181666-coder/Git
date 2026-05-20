
#!/usr/bin/env python3
"""
检查39.9团购单价显示为69.8的问题
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

# 查询最近的团购订单数据
sql = """
SELECT 
    od.store_id,
    s.store_name,
    od.data_date,
    od.order_no,
    od.source_channel,
    od.actual_amount,
    od.should_amount,
    od.order_type,
    od.room_no,
    psd.package,
    psd.product_name
FROM order_detail od
JOIN stores s ON od.store_id = s.id
LEFT JOIN product_sales_detail psd ON od.order_no = psd.order_no AND od.data_date = psd.data_date
WHERE od.data_date >= '2026-05-08' AND od.data_date <= '2026-05-10'
    AND od.source_channel IN ('抖音', '美团大众', '线下团购')
    AND (psd.package LIKE '%39.9%' OR psd.package LIKE '%团购%')
ORDER BY od.data_date, s.store_name, od.actual_amount DESC
LIMIT 100
"""

df = query(sql)

if not df.empty:
    print(f"\n共 {len(df)} 条记录\n")
    
    # 查找包含39.9的套餐
    print("=" * 60)
    print("【1】所有包含'39.9'或'团购'的订单")
    print("=" * 60)
    
    for _, row in df.head(20).iterrows():
        print(f"\n门店: {row['store_name']}")
        print(f"日期: {row['data_date']}")
        print(f"订单号: {row['order_no'][:20]}...")
        print(f"来源: {row['source_channel']}")
        print(f"实际金额: {row['actual_amount']}元")
        print(f"应收金额: {row['should_amount']}元")
        print(f"套餐名: {row['package']}")
        print(f"商品: {row['product_name']}")
        print("-" * 40)
    
    # 统计每个套餐的平均价格
    print("\n" + "=" * 60)
    print("【2】按套餐统计（销售金额 / 数量）")
    print("=" * 60)
    
    pkg_stats = df.groupby(['store_name', 'package']).agg(
        订单数=('order_no', 'count'),
        总销售额=('actual_amount', 'sum'),
        平均单价=('actual_amount', 'mean')
    ).reset_index()
    
    pkg_stats = pkg_stats.sort_values('总销售额', ascending=False)
    
    for _, row in pkg_stats.head(15).iterrows():
        print(f"\n【{row['store_name']}】{row['package']}")
        print(f"   订单数: {row['订单数']}")
        print(f"   总销售额: {row['总销售额']:.0f}元")
        print(f"   平均单价(=总销售额/订单数): {row['平均单价']:.2f}元")

else:
    print("没有找到数据")

# 再查一个更简单的查询
print("\n" + "=" * 60)
print("【3】直接查询order_detail中团购订单的实际金额分布")
print("=" * 60)

sql_simple = """
SELECT 
    s.store_name,
    od.source_channel,
    COUNT(*) as 订单数,
    SUM(od.actual_amount) as 总销售额,
    AVG(od.actual_amount) as 平均单价,
    MIN(od.actual_amount) as 最低价,
    MAX(od.actual_amount) as 最高价
FROM order_detail od
JOIN stores s ON od.store_id = s.id
WHERE od.data_date = '2026-05-10'
    AND od.source_channel IN ('抖音', '美团大众', '线下团购')
GROUP BY s.store_name, od.source_channel
HAVING COUNT(*) > 5
ORDER BY 总销售额 DESC
"""

df_summary = query(sql_simple)

if not df_summary.empty:
    for _, row in df_summary.iterrows():
        print(f"\n{row['store_name']} - {row['source_channel']}:")
        print(f"  订单数: {row['订单数']}")
        print(f"  平均单价: {row['平均单价']:.2f}元 (范围: {row['最低价']:.0f}-{row['最高价']:.0f})")
        print(f"  总销售额: {row['总销售额']:.0f}元")
