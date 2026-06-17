#!/usr/bin/env python3
import pandas as pd
import pymysql
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name

def convert_phone(x):
    if pd.isna(x):
        return None
    try:
        if isinstance(x, float):
            return str(int(x))
        return str(x).strip()
    except:
        return None

def main():
    print('开始导入2025年储值数据...')
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    f = 'data/backup/member_balance/25年储值.xlsx'
    df = pd.read_excel(f)
    print(f'文件总行数: {len(df)}')

    count = 0
    skipped = 0

    for idx, row in df.iterrows():
        try:
            store_name = simplify_store_name(str(row.get('门店', '')))
            if not store_name:
                skipped += 1
                continue

            cursor.execute('SELECT id FROM stores WHERE store_name = %s', (store_name,))
            result = cursor.fetchone()
            if not result:
                skipped += 1
                continue
            store_id = result[0]

            date_val = row.get('日期')
            if pd.isna(date_val):
                skipped += 1
                continue
            ds = pd.to_datetime(date_val).strftime('%Y-%m-%d')

            member_phone = convert_phone(row.get('客户电话'))
            if not member_phone or member_phone == 'nan':
                skipped += 1
                continue

            stored_amount = float(row.get('储值实收', 0) or 0)

            cursor.execute('''
                INSERT INTO stored_value
                (store_id, data_date, member_phone, stored_amount, stored_count, recharge_source)
                VALUES (%s, %s, %s, %s, 1, '历史导入')
            ''', (store_id, ds, member_phone, stored_amount))
            count += 1

        except Exception as e:
            skipped += 1
            pass

        if count % 10000 == 0 and count > 0:
            print(f'  已导入 {count} 条...')
            conn.commit()

    conn.commit()
    print(f'导入完成: {count}条, 跳过: {skipped}条')

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
