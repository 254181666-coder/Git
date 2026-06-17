#!/usr/bin/env python3
import pandas as pd
import pymysql
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name


def calc_period(hour):
    if hour is None:
        return ''
    if 9 <= hour < 18:
        return '日场'
    elif 18 <= hour < 24:
        return '晚场'
    else:
        return '午夜场'


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
    print('导入2026年1-2月订单消费数据...')
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    files = [
        'data/source/order_export_19331_20260424232703.csv',
        'data/source/order_export_19332_20260424233003.csv',
        'data/source/order_export_19333_20260424233545.csv',
    ]

    total_count = 0
    for f in files:
        print(f'\n处理: {Path(f).name}')
        df = pd.read_csv(f, encoding='gbk')
        print(f'  总行数: {len(df)}')

        count = 0
        for _, row in df.iterrows():
            try:
                store_name = simplify_store_name(str(row.get('门店', '')))
                if not store_name:
                    continue

                cursor.execute('SELECT id FROM stores WHERE store_name = %s', (store_name,))
                result = cursor.fetchone()
                if result:
                    store_id = result[0]
                else:
                    continue

                open_time_str = row.get('开房时间', '')
                close_time_str = row.get('关房时间', '')

                open_time = None
                close_time = None
                data_date = None

                if pd.notna(open_time_str):
                    try:
                        open_time = pd.to_datetime(open_time_str)
                        data_date = open_time.date()
                    except:
                        pass

                if pd.notna(close_time_str):
                    try:
                        close_time = pd.to_datetime(close_time_str)
                    except:
                        pass

                if open_time:
                    time_period = calc_period(open_time.hour)
                else:
                    time_period = str(row.get('开房时段', ''))

                customer_phone = convert_phone(row.get('开房人手机号', ''))

                cursor.execute('''
                    INSERT INTO order_detail
                    (store_id, data_date, time_period, room_type, room_no,
                     open_time, close_time, customer_name, customer_phone, order_no,
                     should_amount, actual_amount, room_fee, product_fee, source_channel, scene)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    store_id,
                    data_date,
                    time_period,
                    str(row.get('开房类型', '')),
                    str(row.get('包厢号', '')),
                    open_time,
                    close_time,
                    str(row.get('开房人姓名', '')),
                    customer_phone if customer_phone else '',
                    str(row.get('开台单号', '')),
                    float(row.get('应收金额', 0) or 0),
                    float(row.get('实收金额', 0) or 0),
                    float(row.get('房费收入', 0) or 0),
                    float(row.get('商品收入', 0) or 0),
                    str(row.get('来源渠道', '')),
                    str(row.get('场景', ''))
                ))
                count += 1
            except:
                pass

        print(f'  导入: {count}条')
        conn.commit()
        total_count += count

    cursor.close()
    conn.close()
    print(f'\n总计导入: {total_count}条')


if __name__ == '__main__':
    main()
