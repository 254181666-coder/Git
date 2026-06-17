#!/usr/bin/env python3
import pandas as pd
import pymysql
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG


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
    print('导入会员余额变动明细...')
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    source_dir = PROJECT_ROOT / 'data' / 'source'
    files = sorted(source_dir.glob('会员余额变动明细*.xlsx'))

    print(f'找到 {len(files)} 个文件')

    total_count = 0
    for f in files:
        print(f'\n处理: {f.name}')
        df = pd.read_excel(f)
        df.columns = [c.strip().replace('::multi-filter', '') for c in df.columns]
        print(f'  总行数: {len(df)}')

        count = 0
        for _, row in df.iterrows():
            try:
                change_type = str(row.get('变动类型', ''))
                if change_type == '合计':
                    continue

                change_time = row.get('变动时间')
                if pd.isna(change_time):
                    continue

                try:
                    ct = pd.to_datetime(change_time)
                except:
                    continue

                member_phone = convert_phone(row.get('会员电话', ''))
                if not member_phone:
                    member_phone = ''

                cursor.execute('''
                    INSERT INTO member_balance_change
                    (member_id, member_name, member_phone, member_level,
                     card_store, change_store, change_type,
                     principal_change, principal_balance,
                     gift_change, gift_balance,
                     room_no, remark, change_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    str(row.get('会员号', '')),
                    str(row.get('会员姓名', '')),
                    member_phone,
                    str(row.get('会员等级', '')),
                    str(row.get('建卡门店', '')),
                    str(row.get('本次变动门店', '')),
                    change_type,
                    float(row.get('本金(变动)', 0) or 0),
                    float(row.get('本金(余额)', 0) or 0),
                    float(row.get('赠金(变动)', 0) or 0),
                    float(row.get('赠金(余额)', 0) or 0),
                    str(row.get('包厢号', '')),
                    str(row.get('操作人/备注', '')),
                    ct.strftime('%Y-%m-%d %H:%M:%S')
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
