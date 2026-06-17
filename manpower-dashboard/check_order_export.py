
#!/usr/bin/env python3
"""
读取下载文件夹里的 order_export CSV 文件，检查数据范围
"""
import sys
import os
import pandas as pd
from pathlib import Path

csv_path = Path("/Users/ann/Downloads/order_export_19744_20260429135505.csv")

print("=" * 80)
print(f"🔍 检查 order_export 文件: {csv_path.name}")
print("=" * 80)

if not csv_path.exists():
    print("❌ 文件不存在！")
    sys.exit(1)

# 读取 CSV
df = pd.read_csv(csv_path, encoding='gbk', low_memory=False)
print(f"\n✅ 文件读取成功！共 {len(df)} 条记录")

# 检查关键列
print("\n列名:")
for col in df.columns[:20]:
    print(f"  - {col}")

# 检查日期范围
if '开房时间' in df.columns:
    df['data_date'] = pd.to_datetime(df['开房时间']).dt.date
    print(f"\n日期范围:")
    print(f"  最小: {df['data_date'].min()}")
    print(f"  最大: {df['data_date'].max()}")
    print(f"\n按日期统计:")
    date_stats = df.groupby('data_date').size().sort_index(ascending=False)
    print(date_stats)

# 检查时段
if '开房时段' in df.columns:
    print(f"\n\n时段分布:")
    print(df['开房时段'].value_counts())

print("\n" + "=" * 80)
print("✅ 文件检查完成")
print("=" * 80)
