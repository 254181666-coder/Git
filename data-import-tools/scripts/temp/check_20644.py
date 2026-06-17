#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"

file_path = SOURCE_DIR / "日营业数据表_20644.xlsx"
if file_path.exists():
    df = pd.read_excel(file_path)
    print(f"文件: {file_path.name}")
    print(f"列: {df.columns.tolist()}")
    if '日期' in df.columns:
        dates = df['日期'].dropna().unique()
        print(f"包含的日期: {sorted(dates)}")
        print("\n前3行:")
        print(df.head(3))
