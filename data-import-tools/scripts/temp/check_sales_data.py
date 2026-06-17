#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
import pymysql
from config import MYSQL_CONFIG
from utils import simplify_store_name

print('='*80)
print('检查商品销售数据')
print('='*80)

print('\n=== 1. 查看源Excel文件内容 ===')
source_file = Path('data/archive/source_2026_04_26/商品销售汇总_2026_04_26.xlsx')
if source_file.exists():
    df = pd.read_excel(source_file)
    print(f'总行数: {len(df)}')
    print(f'列名: {df.columns.tolist()}')
    print(f'\n前10行:')
    print(df.head(10))
    
    print(f'\n数据中的日期值（唯一）:')
    unique_dates = df['日期'].unique()
    for d in unique_dates[:10]:
        print(f'  - {d}')

print('\n=== 2. 检查数据库product_sales表 ===')
conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()
cursor.execute('DESCRIBE product_sales')
print('product_sales表结构:')
for col in cursor.fetchall():
    print(f'  - {col[0]} ({col[1]})')

print('\n数据库中4月25日的数据行数:')
cursor.execute("SELECT COUNT(*) FROM product_sales WHERE data_date = '2026-04-25'")
count_25 = cursor.fetchone()[0]
print(f'  2026-04-25: {count_25} 行')

print('\n按门店查看4月25日的记录数:')
cursor.execute("""
    SELECT s.store_name, COUNT(*) as cnt
    FROM product_sales ps
    JOIN stores s ON ps.store_id = s.id
    WHERE ps.data_date = '2026-04-25'
    GROUP BY s.store_name
""")
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条')

cursor.close()
conn.close()
