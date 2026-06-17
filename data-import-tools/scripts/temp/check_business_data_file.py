#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"

print("=" * 80)
print("检查日营业数据表_20268.xlsx 内容")
print("=" * 80)

f = DOWNLOADS / "日营业数据表_20268.xlsx"
if f.exists():
    print(f"\n读取文件...")
    
    try:
        df = pd.read_excel(f, engine='openpyxl')
        print(f"行数: {len(df)}")
        print(f"列名: {list(df.columns)}")
        print("\n前3行数据:")
        print(df.head(3))
        
        # 查看日期列
        if len(df.columns) > 0:
            for col in df.columns:
                print(f"\n列 {col} 的唯一值: {df[col].dropna().unique()[:10]}")
    except Exception as e:
        print(f"错误: {e}")
else:
    print("\n文件不存在!")

print("\n" + "=" * 80)
