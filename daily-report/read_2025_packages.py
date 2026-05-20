
#!/usr/bin/env python3
"""
读取2025年团购内容
"""
import sys
from pathlib import Path

import pandas as pd

# 读取2025年团购内容
file_path = Path("/Users/ann/Desktop/25年团购内容.xlsx")

print("=" * 80)
print("读取2025年团购内容")
print("=" * 80)

# 读取所有sheet
xl = pd.ExcelFile(file_path)
print(f"\nSheet列表: {xl.sheet_names}")

for sheet_name in xl.sheet_names:
    print(f"\n{'=' * 60}")
    print(f"Sheet: {sheet_name}")
    print('=' * 60)
    
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    print(f"行数: {len(df)}, 列数: {len(df.columns)}")
    print(f"\n列名: {df.columns.tolist()}")
    print(f"\n前20行数据:")
    print(df.head(20).to_string(index=False))
