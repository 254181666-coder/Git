#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

# 检查归档目录里的文件
target_file = None
for d in ["source_2026_05_10", "source_history"]:
    dir_path = ARCHIVE_DIR / d
    if dir_path.exists():
        for f in dir_path.iterdir():
            if f.name.startswith("日营业数据表_20644"):
                target_file = f
                break

if target_file:
    print("=" * 80)
    print(f"检查文件: {target_file}")
    print("=" * 80)
    df = pd.read_excel(target_file)
    print(f"列: {df.columns.tolist()}")
    if '日期' in df.columns:
        dates = df['日期'].dropna().unique()
        print(f"\n包含的日期: {sorted(dates)}")
        print(f"\n总记录数: {len(df)}")
        print("\n前 3 行:")
        print(df.head(3))
