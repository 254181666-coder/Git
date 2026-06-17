#!/usr/bin/env python3
"""
导入卡券明细数据到 card_detail 表
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def create_card_detail_table():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_detail (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_time DATETIME DEFAULT NULL,
        coupon_code VARCHAR(100) DEFAULT '',
        member VARCHAR(100) DEFAULT '',
        member_phone VARCHAR(20) DEFAULT '',
        card_name VARCHAR(200) DEFAULT '',
        sale_activity VARCHAR(200) DEFAULT '',
        activity_amount DECIMAL(12,2) DEFAULT 0,
        card_type VARCHAR(100) DEFAULT '',
        issue_store VARCHAR(200) DEFAULT '',
        change_type VARCHAR(100) DEFAULT '',
        change_quantity INT DEFAULT 0,
        remaining_coupons INT DEFAULT NULL,
        remaining_card_packages VARCHAR(200) DEFAULT '',
        verify_store VARCHAR(200) DEFAULT '',
        verify_room VARCHAR(50) DEFAULT '',
        verify_time DATETIME DEFAULT NULL,
        verify_order_no VARCHAR(100) DEFAULT '',
        discount_amount DECIMAL(12,2) DEFAULT 0,
        operator VARCHAR(100) DEFAULT '',
        remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_event_time (event_time),
        INDEX idx_coupon_code (coupon_code),
        INDEX idx_member_phone (member_phone)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("卡券明细表创建成功")


def import_card_detail_files(file_paths):
    create_card_detail_table()

    conn = get_conn()
    cursor = conn.cursor()

    total_count = 0

    for file_path in file_paths:
        print(f"\n导入文件: {Path(file_path).name}")
        df = pd.read_csv(file_path, encoding='gbk')
        print(f"  总行数: {len(df)}")

        count = 0
        for _, row in df.iterrows():
            try:
                event_time = None
                et = row.get('时间')
                if pd.notna(et):
                    try:
                        event_time = pd.to_datetime(et).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                verify_time = None
                vt = row.get('核销时间')
                if pd.notna(vt):
                    try:
                        verify_time = pd.to_datetime(vt).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # 处理优惠金额（去除"元"字）
                discount_amount = 0
                discount_amount_val = row.get('优惠金额')
                if pd.notna(discount_amount_val):
                    discount_amount_str = str(discount_amount_val)
                    discount_amount = float(discount_amount_str.replace('元', '').strip())

                # 处理活动售卖金额
                activity_amount = 0
                activity_amount_val = row.get('活动售卖金额')
                if pd.notna(activity_amount_val):
                    try:
                        val_str = str(activity_amount_val).strip()
                        if val_str and val_str not in ('/', '-'):
                            activity_amount = float(val_str)
                    except:
                        pass

                # 处理变动数量
                change_quantity = 0
                change_quantity_val = row.get('变动数量')
                if pd.notna(change_quantity_val):
                    try:
                        change_quantity = int(str(change_quantity_val).strip())
                    except:
                        pass

                # 处理变动后剩余优惠券数量
                remaining_coupons = None
                remaining_coupons_val = row.get('变动后剩余优惠券数量')
                if pd.notna(remaining_coupons_val):
                    try:
                        remaining_coupons = int(remaining_coupons_val)
                    except:
                        pass

                # 处理变动后剩余卡包数量 - 这个字段是字符串，不是数字
                remaining_card_packages_str = str(row.get('变动后剩余卡包数量', '')) if pd.notna(row.get('变动后剩余卡包数量')) else ''

                cursor.execute('''
                INSERT INTO card_detail
                (event_time, coupon_code, member, member_phone, card_name, sale_activity,
                 activity_amount, card_type, issue_store, change_type, change_quantity,
                 remaining_coupons, remaining_card_packages, verify_store, verify_room,
                 verify_time, verify_order_no, discount_amount, operator, remark)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    event_time,
                    str(row.get('券码', '')) if pd.notna(row.get('券码')) else '',
                    str(row.get('会员', '')) if pd.notna(row.get('会员')) else '',
                    str(row.get('会员手机号', '')) if pd.notna(row.get('会员手机号')) else '',
                    str(row.get('卡券名称', '')) if pd.notna(row.get('卡券名称')) else '',
                    str(row.get('售卖活动', '')) if pd.notna(row.get('售卖活动')) else '',
                    activity_amount,
                    str(row.get('类型', '')) if pd.notna(row.get('类型')) else '',
                    str(row.get('发放门店', '')) if pd.notna(row.get('发放门店')) else '',
                    str(row.get('变动类型', '')) if pd.notna(row.get('变动类型')) else '',
                    change_quantity,
                    remaining_coupons,
                    remaining_card_packages_str,
                    str(row.get('核销门店', '')) if pd.notna(row.get('核销门店')) else '',
                    str(row.get('核销包厢', '')) if pd.notna(row.get('核销包厢')) else '',
                    verify_time,
                    str(row.get('核销订单号', '')) if pd.notna(row.get('核销订单号')) else '',
                    discount_amount,
                    str(row.get('操作人', '')) if pd.notna(row.get('操作人')) else '',
                    str(row.get('备注', '')) if pd.notna(row.get('备注')) else ''
                ))
                count += 1
            except Exception as e:
                pass

        conn.commit()
        total_count += count
        print(f"  导入 {count} 条记录")

    cursor.close()
    conn.close()
    print(f"\n总计导入 {total_count} 条记录")
    return total_count


def main():
    script_dir = Path(__file__).parent.parent
    source_dir = script_dir / "data" / "source"
    files = sorted(source_dir.glob("card_detail*.csv"))

    if not files:
        print("未找到 card_detail*.csv 文件")
        return

    print("=" * 60)
    print(f"卡券明细导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"找到 {len(files)} 个文件:")
    for f in files:
        print(f"  - {f.name}")

    import_card_detail_files([str(f) for f in files])

    print("=" * 60)
    print("导入完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
