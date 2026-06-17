#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
desktop_path = Path.home() / "Desktop"

print("查看桌面上的日营业数据表文件...")

# 查找日营业数据表_21109相关的文件
possible_names = [
    "日营业数据表_21109.xlsx",
    "日营业数据表_21109.xls",
    "日营业数据表_21109.csv"
]

target_file = None
for name in possible_names:
    file_path = desktop_path / name
    if file_path.exists():
        target_file = file_path
        print(f"✓ 找到文件: {target_file.name}")
        break

if not target_file:
    print("未找到日营业数据表_21109文件，查看桌面所有文件：")
    for f in desktop_path.iterdir():
        if "日营业" in f.name or "21109" in f.name:
            print(f"  - {f.name}")
    sys.exit(1)

print("\n读取文件内容...")
df = pd.read_excel(target_file)

print(f"\n文件形状: {df.shape}")
print(f"\n列名: {df.columns.tolist()}")
print(f"\n前10行数据:")
print(df.head(10).to_string())

print(f"\n检查日期列...")
if "日期" in df.columns:
    print(f"\n唯一日期值: {df['日期'].unique()}")
    
print("\n检查门店列...")
if "门店" in df.columns:
    print(f"唯一门店值: {df['门店'].dropna().unique()}")

print("\n数据预览完成！")
