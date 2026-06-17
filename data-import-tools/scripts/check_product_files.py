#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"


def check_product_sales_files():
    print("=" * 70)
    print("商品销售明细文件检查")
    print("=" * 70)

    files = sorted(SOURCE_DIR.glob("商品销售明细*2026*.xlsx"))

    print(f"\n找到 {len(files)} 个文件:\n")

    date_groups = {}

    for f in files:
        if '副本' in f.name:
            continue

        match = re.search(r'(\d{4})[_-](\d{2})[_-](\d{2})', f.name)
        if match:
            date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        else:
            match2 = re.search(r'(\d{4})[_-](\d{1,2})[_-](\d{1,2})', f.name)
            if match2:
                date_str = f"{match2.group(1)}-{int(match2.group(2)):02d}-{int(match2.group(3)):02d}"
            else:
                date_str = "未知日期"

        if date_str not in date_groups:
            date_groups[date_str] = []
        date_groups[date_str].append(f.name)

    for date_str in sorted(date_groups.keys()):
        files_list = date_groups[date_str]
        print(f"\n📅 {date_str}: {len(files_list)} 个文件")

        sample_file_name = files_list[0]
        sample_file_path = SOURCE_DIR / sample_file_name

        if sample_file_path.exists():
            try:
                df = pd.read_excel(sample_file_path, nrows=5)
                print(f"   示例: {sample_file_name}")
                print(f"   列名: {list(df.columns)[:5]}...")
                print(f"   前几行数据预览:")
                for idx, row in df.head(3).iterrows():
                    store = row.get('门店', 'N/A')
                    product = row.get('商品名字', 'N/A')
                    date_val = row.get('日期', 'N/A')
                    print(f"     行{idx+1}: 门店={store}, 商品={product}, 日期={date_val}")
            except Exception as e:
                print(f"   读取错误: {e}")

    print("\n" + "=" * 70)
    print("文件清单汇总:")
    print("=" * 70)

    for date_str in sorted(date_groups.keys()):
        files_list = date_groups[date_str]
        print(f"\n【{date_str}】共 {len(files_list)} 个文件:")
        for fn in sorted(files_list):
            print(f"  - {fn}")

    total_files = sum(len(v) for v in date_groups.values())
    print(f"\n总计: {total_files} 个文件")
    print("=" * 70)


if __name__ == "__main__":
    check_product_sales_files()
