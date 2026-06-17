#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

source_dir = Path('data/source')

print('='*80)
print('储值提成明细表:')
f = next(source_dir.glob('储值提成明细表*.xlsx'), None)
if f:
    df = pd.read_excel(f)
    print('  列名:', df.columns.tolist())
    print('  前3行:')
    print(df.head(3))

print('\n' + '='*80)
print('商品提成明细表:')
f = next(source_dir.glob('商品提成明细表*.xlsx'), None)
if f:
    df = pd.read_excel(f)
    print('  列名:', df.columns.tolist())
    print('  前3行:')
    print(df.head(3))

print('\n' + '='*80)
print('card_detail CSV:')
f = next(source_dir.glob('card_detail*.csv'), None)
if f:
    df = pd.read_csv(f, encoding='gbk', nrows=5)
    print('  列名:', df.columns.tolist())
    print('  前3行:')
    print(df.head(3))
