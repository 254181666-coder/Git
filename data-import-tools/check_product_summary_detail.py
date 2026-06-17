#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
downloads_dir = Path("/Users/ann/Downloads")

print("检查商品销售汇总文件的内容：")
print("-" * 80)

f = downloads_dir / "商品销售汇总_2026_05_16.xlsx"
if f.exists():
    df = pd.read_excel(f)
    print(f"\n文件：{f.name}")
    print(f"列名：{list(df.columns)}")
    
    # 检查日期列
    if '日期' in df.columns:
        dates = df['日期'].dropna()
        if len(dates) > 0:
            print(f"\n日期列的前10个值：")
            for i, d in enumerate(dates[:10]):
                try:
                    dt = pd.to_datetime(d)
                    print(f"  {i+1}: {dt.strftime('%Y-%m-%d')}")
                except:
                    print(f"  {i+1}: {d}")
            
            # 统计唯一日期
            unique_dates = []
            for d in dates:
                try:
                    dt = pd.to_datetime(d)
                    date_str = dt.strftime('%Y-%m-%d')
                    if date_str not in unique_dates:
                        unique_dates.append(date_str)
                except:
                    pass
            print(f"\n文件包含的唯一日期：{unique_dates}")

# 检查商品销售明细
f2 = downloads_dir / "商品销售明细_-_商品+包厢维度_2026_05_16.xlsx"
if f2.exists():
    df2 = pd.read_excel(f2)
    print(f"\n\n文件：{f2.name}")
    if '销售日期' in df2.columns:
        dates2 = df2['销售日期'].dropna()
        if len(dates2) > 0:
            unique_dates2 = []
            for d in dates2:
                try:
                    dt = pd.to_datetime(d)
                    date_str = dt.strftime('%Y-%m-%d')
                    if date_str not in unique_dates2:
                        unique_dates2.append(date_str)
                except:
                    pass
            print(f"文件包含的唯一日期：{unique_dates2}")
