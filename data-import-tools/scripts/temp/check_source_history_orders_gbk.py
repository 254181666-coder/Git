#!/usr/bin/env python3
"""用gbk编码检查source_history目录中的order_export文件内容"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

source_history_dir = PROJECT_ROOT / "data" / "archive" / "source_history"

print("=" * 80)
print("用gbk编码检查source_history中的order_export文件")
print("=" * 80)

order_files = list(source_history_dir.glob("order_export*.csv"))
order_files.sort(key=lambda f: f.name)

found_data_dates = []

for f in order_files:
    print(f"\n--- {f.name} ---")
    
    try:
        # 用gbk读取
        df = pd.read_csv(f, nrows=10, encoding='gbk')
        print(f"  文件总列数：{len(df.columns)}")
        print(f"  前几列名：{list(df.columns[:10])}")
        
        # 查看完整文件
        df_full = pd.read_csv(f, encoding='gbk')
        print(f"  文件总记录数：{len(df_full)}")
        
        # 尝试找到日期列
        # 根据之前的经验，order_detail中有open_time, data_date等列
        for col in df_full.columns:
            sample = df_full[col].dropna().head(5)
            if len(sample) > 0:
                first_val = str(sample.iloc[0])
                if '2026-' in first_val:
                    print(f"\n  列 '{col}' 包含日期：")
                    unique_dates = df_full[col].dropna().unique()
                    if len(unique_dates) <= 15:
                        print(f"    唯一日期：{sorted(unique_dates)}")
                        found_data_dates.extend([d for d in unique_dates if d.startswith('2026-05-')])
        
    except Exception as e:
        print(f"  读取失败：{e}")

print("\n" + "=" * 80)
print("发现的5月份日期：", sorted(list(set(found_data_dates))))
print("=" * 80)
