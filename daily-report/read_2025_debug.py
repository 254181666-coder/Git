
#!/usr/bin/env python3
"""
调试读取2025年团购内容
"""
import sys
from pathlib import Path

import pandas as pd

# 读取2025年团购内容
file_path = Path("/Users/ann/Desktop/25年团购内容.xlsx")

print("=" * 80)
print("读取2025年团购内容 - 调试")
print("=" * 80)

# 读取抖音Sheet
df_douyin = pd.read_excel(file_path, sheet_name='抖音')
print("\n【抖音Sheet】")
print(f"总行数: {len(df_douyin)}")
print(f"\n前30行数据:")
for idx in range(min(30, len(df_douyin))):
    row = df_douyin.iloc[idx]
    print(f"行{idx}: ", end='')
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            print(f"[{col_idx}]{val} | ", end='')
    print()

print("\n\n" + "=" * 80)
print("\n【美团Sheet】")
df_meituan = pd.read_excel(file_path, sheet_name='Sheet2')
print(f"总行数: {len(df_meituan)}")
print(f"\n前30行数据:")
for idx in range(min(30, len(df_meituan))):
    row = df_meituan.iloc[idx]
    print(f"行{idx}: ", end='')
    for col_idx, val in enumerate(row):
        if pd.notna(val):
            print(f"[{col_idx}]{val} | ", end='')
    print()
