#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

archive_dir = Path('data/archive')
files = sorted(archive_dir.rglob('会员储值订单表*.xlsx'))

print('=' * 80)
print('只统计4月份的数据 (2026-04-01 到 2026-04-30)')
print('=' * 80)

april_total = 0
april_files = []

for f in files:
    df = pd.read_excel(f)
    count = 0
    
    if '充值时间' in df.columns:
        for val in df['充值时间']:
            if pd.notna(val):
                try:
                    d = pd.to_datetime(val)
                    ds = d.strftime('%Y-%m-%d')
                    if '2026-04' in ds:
                        count += 1
                except:
                    pass
    
    if count > 0:
        april_total += count
        april_files.append((f, count))
        print(f'{f.relative_to(archive_dir.parent)}: {count} 条')

print(f'\n总计4月数据: {april_total} 条')
