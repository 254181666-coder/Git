#!/usr/bin/env python3
import pandas as pd

# 读取生成的结果文件
result_file = '备品统计_包含6月待客量.xlsx'
df = pd.read_excel(result_file)

print(f"结果文件形状: {df.shape}")
print("\n列名:")
for col in df.columns:
    print(f"  - {col}")

print("\n前5行数据:")
print(df.head())
