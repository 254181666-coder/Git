#!/usr/bin/env python3
"""检查source_history目录中的order_export文件内容，确认它们的数据日期"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

source_history_dir = PROJECT_ROOT / "data" / "archive" / "source_history"

print("=" * 80)
print("检查source_history中的order_export文件")
print("=" * 80)

order_files = list(source_history_dir.glob("order_export*.csv"))
order_files.sort(key=lambda f: f.name)

for f in order_files:
    print(f"\n--- {f.name} ---")
    
    try:
        df = pd.read_csv(f, nrows=5)
        print(f"  前5行预览：")
        for i, row in df.head(3).iterrows():
            print(f"    行{i}: {row.tolist()[:5]}")
        
        # 尝试找到日期相关的列
        if len(df.columns) > 0:
            # 查看文件中所有数据的日期
            df_full = pd.read_csv(f)
            print(f"\n  文件总记录数：{len(df_full)}")
            
            # 查找date、日期、open_time、开房时间等类似列
            date_cols = []
            for col in df_full.columns:
                col_lower = str(col).lower()
                if 'date' in col_lower or '日期' in col_lower or 'time' in col_lower:
                    date_cols.append(col)
            
            print(f"\n  可能包含日期的列：{date_cols}")
            
            # 尝试找到数据日期（data_date）
            for col in df_full.columns:
                # 检查这列的内容
                sample_vals = df_full[col].dropna().head(10).astype(str).tolist()
                if any('2026-' in v for v in sample_vals):
                    print(f"\n  列 '{col}' 看起来包含日期：")
                    print(f"    样本值：{sample_vals[:3]}")
                    
                    # 查看唯一值
                    unique_dates = df_full[col].dropna().unique()
                    if len(unique_dates) <= 10:
                        print(f"    唯一日期值：{unique_dates}")
                    
    except Exception as e:
        print(f"  读取失败：{e}")

print("\n" + "=" * 80)
