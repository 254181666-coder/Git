#!/usr/bin/env python3
import sys
from pathlib import Path

downloads_dir = Path("/Users/ann/Downloads")

print("下载文件夹里的所有数据相关文件：")
print("-" * 60)

# 查找所有相关文件
patterns = [
    "日营业数据表*.xlsx",
    "会员储值订单表*.xlsx",
    "商品销售明细*.xlsx",
    "商品销售汇总*.xlsx",
    "储值提成明细表*.xlsx",
    "商品提成明细表*.xlsx",
    "会员余额变动明细*.xlsx",
    "order_export*.csv",
    "card_detail*.csv"
]

for pattern in patterns:
    files = list(downloads_dir.glob(pattern))
    if files:
        print(f"\n{pattern}:")
        for f in sorted(files):
            print(f"  - {f.name}")
