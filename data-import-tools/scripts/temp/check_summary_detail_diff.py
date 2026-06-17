#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print("对比商品汇总表和明细表的区别")
    print("=" * 80)
    
    # 汇总表
    summary_path = PROJECT_ROOT / "data" / "source" / "商品销售汇总_2026_04_26.xlsx"
    if summary_path.exists():
        df_summary = pd.read_excel(summary_path)
        print(f"\n【商品销售汇总表】列:")
        for col in df_summary.columns:
            print(f"  - {col}")
        print(f"\n汇总表前3行:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 200)
        print(df_summary.head(3))
    
    # 明细表
    detail_path = PROJECT_ROOT / "data" / "source" / "商品销售明细_-_商品+包厢维度_2026_04_26.xlsx"
    if detail_path.exists():
        df_detail = pd.read_excel(detail_path)
        print(f"\n【商品销售明细表】列:")
        for col in df_detail.columns:
            print(f"  - {col}")
        print(f"\n明细表前3行:")
        print(df_detail.head(3))
    
    # 对比区别
    print(f"\n" + "=" * 80)
    print("对比总结:")
    print(f"=" * 80)
    
    if summary_path.exists() and detail_path.exists():
        summary_cols = set(df_summary.columns)
        detail_cols = set(df_detail.columns)
        
        print(f"\n汇总表有但明细表没有的列:")
        for col in sorted(summary_cols - detail_cols):
            print(f"  - {col}")
        
        print(f"\n明细表有但汇总表没有的列:")
        for col in sorted(detail_cols - summary_cols):
            print(f"  - {col}")
        
        print(f"\n" + "关键区别:")
        print(f"  汇总表: 有 '系统销售类别::multi-filter' 列，可以映射big_category")
        print(f"  明细表: 没有 '系统销售类别::multi-filter' 列，只有 '套餐' 列！")

if __name__ == "__main__":
    main()
