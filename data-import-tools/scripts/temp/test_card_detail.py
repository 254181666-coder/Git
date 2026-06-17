#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

source_dir = Path('data/source')
f = next(source_dir.glob('card_detail*.csv'))
df = pd.read_csv(f, encoding='gbk')
print(f'总行数: {len(df)}')
print(f'列名: {df.columns.tolist()}')
print('\n前3行数据:')
for i in range(min(3, len(df))):
    print(f'\n第{i+1}行:')
    row = df.iloc[i]
    for col in df.columns:
        val = row[col]
        print(f'  {col}: {val} (type: {type(val)})')
