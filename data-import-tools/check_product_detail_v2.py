#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
downloads_dir = Path("/Users/ann/Downloads")

f2 = downloads_dir / "商品销售明细_-_商品+包厢维度_2026_05_16.xlsx"
if f2.exists():
    df2 = pd.read_excel(f2)
    print(f"文件：{f2.name}")
    
    date_col = None
    if '销售日期::multi-filter' in df2.columns:
        date_col = '销售日期::multi-filter'
    elif '销售日期' in df2.columns:
        date_col = '销售日期'
    
    if date_col:
        dates2 = df2[date_col].dropna()
        if len(dates2) > 0:
            print(f"\n前10个日期值：")
            for i, d in enumerate(dates2[:10]):
                try:
                    dt = pd.to_datetime(d)
                    print(f"  {i+1}: {dt.strftime('%Y-%m-%d')}")
                except:
                    print(f"  {i+1}: {d}")
            
            unique_dates2 = []
            for d in dates2:
                try:
                    dt = pd.to_datetime(d)
                    date_str = dt.strftime('%Y-%m-%d')
                    if date_str not in unique_dates2:
                        unique_dates2.append(date_str)
                except:
                    pass
            print(f"\n文件包含的唯一日期：{unique_dates2}")
