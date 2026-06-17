#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print("检查新 order 文件内容")
    print("=" * 80)
    
    file_path = PROJECT_ROOT / "data" / "source" / "order_export_19742_20260429135024.csv"
    
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return
    
    print(f"\n文件: {file_path.name}")
    print(f"大小: {file_path.stat().st_size} 字节")
    
    df = pd.read_csv(file_path, encoding='gbk')
    print(f"\n总行数: {len(df)}")
    print(f"列: {df.columns.tolist()}")
    
    if '开房时间' in df.columns:
        print(f"\n开房时间样本:")
        sample = df['开房时间'].dropna().head(10)
        for t in sample:
            print(f"  {t}")
        
        unique_dates = set()
        for t in df['开房时间'].dropna():
            try:
                dt = pd.to_datetime(t)
                unique_dates.add(dt.date())
            except:
                pass
        
        print(f"\n唯一日期数: {len(unique_dates)}")
        print(f"日期列表: {sorted(unique_dates)}")

if __name__ == "__main__":
    main()
