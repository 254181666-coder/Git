#!/usr/bin/env python3
import pandas as pd
import pymysql
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name

def main():
    print('开始导入1-3月储值数据...')
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    files = [
        'data/source/会员储值订单表_2026_04_24.xlsx',
        'data/source/会员储值订单表_2026_04_24 (1).xlsx',
        'data/source/会员储值订单表_2026_04_24 (2).xlsx',
    ]

    total_count = 0
    for f in files:
        df = pd.read_excel(f)
        df.columns = [c.strip() for c in df.columns]

        df = df[df['会员等级'] != '合计']

        count = 0
        for _, row in df.iterrows():
            try:
                store_name = simplify_store_name(str(row.get('充值门店', '')))
                if not store_name:
                    continue

                cursor.execute('SELECT id FROM stores WHERE store_name = %s', (store_name,))
                result = cursor.fetchone()
                if result:
                    store_id = result[0]
                else:
                    continue

                time_val = row.get('充值时间')
                if pd.isna(time_val):
                    continue

                dt = pd.to_datetime(time_val)
                data_date = dt.strftime('%Y-%m-%d')

                member_phone = str(row.get('会员电话', ''))
                if not member_phone or member_phone == 'nan':
                    member_phone = ''

                stored_amount = float(row.get('酒水变动本金', 0) or 0)

                cursor.execute('''
                    INSERT INTO stored_value
                    (store_id, data_date, member_level, stored_amount, stored_count, recharge_source,
                     is_first_recharge, marketing_manager, member_name, member_phone,
                     room_principal, room_gift, drink_principal, drink_gift,
                     payment_method, payment_amount, points_change, points_balance,
                     growth_change, growth_balance, total_balance, principal_balance, gift_balance, recharge_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    store_id, data_date,
                    str(row.get('会员等级', '')),
                    stored_amount, 1,
                    str(row.get('充值来源', '')),
                    1 if str(row.get('是否为首充', '否')) == '是' else 0,
                    str(row.get('营销经理', '')),
                    str(row.get('会员姓名', '')),
                    member_phone,
                    float(row.get('房费变动本金', 0) or 0),
                    float(row.get('房费变动赠金', 0) or 0),
                    stored_amount,
                    float(row.get('酒水变动赠金', 0) or 0),
                    str(row.get('支付方式', '')),
                    float(row.get('支付金额', 0) or 0),
                    int(row.get('变动积分', 0) or 0),
                    int(row.get('积分余额', 0) or 0),
                    int(row.get('变动成长值', 0) or 0),
                    int(row.get('成长值余额', 0) or 0),
                    float(row.get('合计余额', 0) or 0),
                    float(row.get('本金余额', 0) or 0),
                    float(row.get('赠送余额', 0) or 0),
                    dt.strftime('%Y-%m-%d %H:%M:%S')
                ))
                count += 1
            except Exception as e:
                pass

        print(f'{f}: 导入 {count} 条')
        total_count += count
        conn.commit()

    cursor.close()
    conn.close()
    print(f'\n总计导入: {total_count} 条')

if __name__ == '__main__':
    main()
