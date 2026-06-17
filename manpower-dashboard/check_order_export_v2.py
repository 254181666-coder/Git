
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
print("\n前10行的开房时间和开房时段:")
for i in range(10):
    open_time = df.iloc[i]['开房时间'] if '开房时间' in df.columns else 'N/A'
    time_period = df.iloc[i]['开房时段'] if '开房时段' in df.columns else 'N/A'
    print(f"  {i+1}: 时间={open_time}, 时段={time_period}")

# 尝试解析日期，跳过错误值
if '开房时间' in df.columns:
    dates = []
    for val in df['开房时间']:
        try:
            dt = pd.to_datetime(val)
            dates.append(dt.date())
        except:
            pass
    if dates:
        print(f"\n✅ 成功解析 {len(dates)} 条日期")
        date_series = pd.Series(dates)
        print(f"  最小日期: {date_series.min()}")
        print(f"  最大日期: {date_series.max()}")
        print(f"\n按日期统计:")
        print(date_series.value_counts().sort_index(ascending=False))

# 检查时段
if '开房时段' in df.columns:
    print(f"\n\n时段分布:")
    print(df['开房时段'].value_counts())

print("\n" + "=" * 80)
print("✅ 文件检查完成")
print("=" * 80)
