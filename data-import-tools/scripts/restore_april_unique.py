#!/usr/bin/env python3
"""
只导入4月份的唯一数据，避免重复
"""
import sys
from pathlib import Path
import pandas as pd
import pymysql
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

def import_single_file(file_path):
    print(f'\n处理文件: {file_path.name}')
    try:
        df = pd.read_excel(file_path)
        print(f'  总行数: {len(df)}')
    except Exception as e:
        print(f'  读取文件失败: {e}')
        return 0

    conn = get_conn()
    cursor = conn.cursor()
    count = 0

    for _, row in df.iterrows():
        try:
            # 检查是否是合计行
            member_level = str(row.get('会员等级', '')).strip()
            if member_level == '合计':
                continue

            store_name_raw = str(row.get('充值门店', ''))
            store_name = simplify_store_name(store_name_raw)
            if not store_name:
                continue

            # 确定日期，只导入4月数据
            data_date = None
            recharge_time = row.get('充值时间')
            if pd.notna(recharge_time):
                try:
                    rt = pd.to_datetime(recharge_time)
                    data_date = rt.strftime('%Y-%m-%d')
                    if not data_date.startswith('2026-04'):
                        continue
                except:
                    continue
            else:
                continue

            # 获取门店ID
            cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
            store_result = cursor.fetchone()
            if not store_result:
                cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
                conn.commit()
                store_id = cursor.lastrowid
            else:
                store_id = store_result[0]

            # 处理金额
            stored_amount = float(row.get('酒水变动本金', 0) or 0)
            is_first_recharge = 1 if str(row.get('是否为首充', '否')) == '是' else 0

            # 插入数据
            cursor.execute('''
                INSERT INTO stored_value
                (store_id, data_date, member_level, stored_amount, stored_count,
                 recharge_source, is_first_recharge, marketing_manager,
                 member_name, member_phone, room_principal, room_gift,
                 drink_principal, drink_gift, payment_method, payment_amount,
                 points_change, points_balance, growth_change, growth_balance,
                 total_balance, principal_balance, gift_balance, recharge_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                store_id, data_date,
                str(row.get('会员等级', '')), stored_amount, 1,
                str(row.get('充值来源', '')), is_first_recharge,
                str(row.get('营销经理', '')), str(row.get('会员姓名', '')),
                str(row.get('会员电话', '')), float(row.get('房费变动本金', 0) or 0),
                float(row.get('房费变动赠金', 0) or 0), float(row.get('酒水变动本金', 0) or 0),
                float(row.get('酒水变动赠金', 0) or 0), str(row.get('支付方式', '')),
                float(row.get('支付金额', 0) or 0), int(row.get('变动积分', 0) or 0),
                int(row.get('积分余额', 0) or 0), int(row.get('变动成长值', 0) or 0),
                int(row.get('成长值余额', 0) or 0), float(row.get('合计余额', 0) or 0),
                float(row.get('本金余额', 0) or 0), float(row.get('赠送余额', 0) or 0),
                str(recharge_time) if pd.notna(recharge_time) else None
            ))
            count += 1
        except Exception as e:
            pass

    conn.commit()
    cursor.close()
    conn.close()
    print(f'  成功导入4月数据: {count} 条')
    return count


def main():
    print('=' * 60)
    print('恢复4月份唯一会员储值订单数据')
    print('=' * 60)

    # 只选择确实包含4月数据的文件，避免重复
    archive_dir = PROJECT_ROOT / 'data/archive'

    files = [
        archive_dir / 'source_2026_04_24/会员储值订单表_2026_04_23.xlsx',
        archive_dir / 'source_2026_04_24/会员储值订单表_2026_04_24.xlsx',
        archive_dir / 'source_2026_04_25/会员储值订单表_2026_04_25.xlsx',
        archive_dir / 'source_2026_04_26/会员储值订单表_2026_04_26.xlsx',
    ]

    print(f'\n找到以下文件（避免重复）:')
    for f in files:
        print(f'  - {f.relative_to(PROJECT_ROOT)}')

    # 逐个导入
    total_count = 0
    for f in files:
        if f.exists():
            cnt = import_single_file(f)
            total_count += cnt

    print('\n' + '=' * 60)
    print(f'全部完成！共导入4月数据: {total_count} 条')
    print('=' * 60)


if __name__ == '__main__':
    main()
