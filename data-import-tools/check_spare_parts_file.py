#!/usr/bin/env python3
import pandas as pd

# 读取Excel文件
file_path = '各店面备品统计.xlsx'
excel_file = pd.ExcelFile(file_path)

print(f"Excel文件包含 {len(excel_file.sheet_names)} 个工作表:")
for sheet_name in excel_file.sheet_names:
    print(f"  - {sheet_name}")
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    print(f"    数据形状: {df.shape}")
    print(f"    列名: {list(df.columns)}")
    print("    前5行数据:")
    print(df.head())
    print("\n" + "="*80 + "\n")
