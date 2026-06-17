#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

archive_dir = Path('data/archive')
files = sorted(archive_dir.rglob('会员储值订单表*.xlsx'))

print('=' * 80)
print('检查每个会员储值订单表文件的日期范围')
print('=' * 80)

for f in files:
    print(f'\n{f.relative_to(archive_dir.parent)}:')
    df = pd.read_excel(f)
    print(f'  总行数: {len(df)}')
    
    # 提取充值时间列
    if '充值时间' in df.columns:
        dates = []
        for val in df['充值时间']:
            if pd.notna(val):
                try:
                    d = pd.to_datetime(val)
                    dates.append(d)
                except:
                    pass
        if dates:
            print(f'  日期范围: {min(dates).strftime("%Y-%m-%d")} 到 {max(dates).strftime("%Y-%m-%d")}')
            # 统计每天的记录数
            daily_counts = {}
            for d in dates:
                ds = d.strftime('%Y-%m-%d')
                daily_counts[ds] = daily_counts.get(ds, 0) + 1
            print(f'  每天记录数:')
            for ds in sorted(daily_counts.keys()):
                print(f'    {ds}: {daily_counts[ds]} 条')
