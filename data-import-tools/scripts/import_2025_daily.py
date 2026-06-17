#!/usr/bin/env python3
import pandas as pd
import pymysql
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG


def excel_date_to_str(excel_date):
    if pd.isna(excel_date):
        return None
    try:
        if isinstance(excel_date, (int, float)):
            date = datetime(1899, 12, 30) + timedelta(days=int(excel_date))
            return date.strftime('%Y-%m-%d')
        elif str(type(excel_date)) == "<class 'datetime.datetime'>" or isinstance(excel_date, datetime):
            return excel_date.strftime('%Y-%m-%d')
        elif isinstance(excel_date, str):
            return str(excel_date)[:10]
    except Exception as e:
        print(f"  date conversion error: {e}")
    return None


def is_valid_date_row(row, date_col=1):
    val = row.iloc[date_col]
    if pd.isna(val):
        return False
    if isinstance(val, (int, float)) and 40000 < val < 50000:
        return True
    if str(type(val)) == "<class 'datetime.datetime'>" or isinstance(val, datetime):
        return True
    if isinstance(val, str) and '2025' in val:
        return True
    return False


def main():
    print('导入25年日营业数据...')
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    f = PROJECT_ROOT / 'data' / 'source' / '25nian.xlsx'
    xl = pd.ExcelFile(f)

    store_mapping = {
        '上东': '上东店',
        ' 佳木斯': '佳木斯店',
        '佳木斯': '佳木斯店',
        '晨宇': '晨宇店',
        '锡盟': '锡盟店',
        ' 松原二': '松原二店',
        '松原二': '松原二店',
        '鸡西': '鸡西店',
        '通化': '通化店',
        '安达': '安达店',
        '松原一': '松原一店',
        '通辽': '通辽店',
        '法库': '法库店',
        '榆树': '榆树店',
    }

    total_count = 0
    store_counts = {}

    for sheet_name in xl.sheet_names:
        store_name_raw = sheet_name.strip()
        store_name = store_mapping.get(store_name_raw, store_name_raw)

        df = pd.read_excel(f, sheet_name=sheet_name)

        store_count = 0
        for _, row in df.iterrows():
            if not is_valid_date_row(row, 1):
                continue
            try:
                excel_date = row.iloc[1]
                data_date = excel_date_to_str(excel_date)
                if not data_date or not data_date.startswith('2025'):
                    continue

                # 获取store_id
                cursor.execute('SELECT id FROM stores WHERE store_name = %s', (store_name,))
                result = cursor.fetchone()
                if result:
                    store_id = result[0]
                else:
                    continue

                total_revenue = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
                stored_card = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0
                times_card = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0
                group_buy = (float(row.iloc[6]) if pd.notna(row.iloc[6]) else 0) + \
                            (float(row.iloc[7]) if pd.notna(row.iloc[7]) else 0)
                customers = int(row.iloc[9]) if pd.notna(row.iloc[9]) else 0

                cursor.execute('''
                    INSERT INTO store_daily
                    (store_id, data_date, total_revenue, stored_card_sales, times_card_sales,
                     online_groupbuy, customers, weekday)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    store_id, data_date, total_revenue, stored_card, times_card,
                    group_buy, customers,
                    str(row.iloc[2]) if pd.notna(row.iloc[2]) else ''
                ))
                store_count += 1
                total_count += 1
            except Exception as e:
                pass

        if store_count > 0:
            store_counts[store_name] = store_count
            print(f'  {sheet_name}: 导入{store_count}条')

    conn.commit()
    cursor.close()
    conn.close()
    print(f'导入完成: {total_count}条')
    for name, cnt in store_counts.items():
        print(f'  {name}: {cnt}')


if __name__ == '__main__':
    main()
