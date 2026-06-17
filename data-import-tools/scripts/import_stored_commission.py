#!/usr/bin/env python3
"""
导入储值提成数据到 stored_commission 表
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


def create_stored_commission_table():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stored_commission (
        id INT AUTO_INCREMENT PRIMARY KEY,
        store_id INT NOT NULL,
        business_date DATE NOT NULL,
        stored_time DATETIME DEFAULT NULL,
        commission_staff VARCHAR(100) DEFAULT '',
        staff_account VARCHAR(100) DEFAULT '',
        member_phone VARCHAR(20) DEFAULT '',
        stored_amount DECIMAL(12,2) DEFAULT 0,
        commission_rule VARCHAR(100) DEFAULT '',
        commission_amount DECIMAL(12,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_store_id (store_id),
        INDEX idx_business_date (business_date),
        INDEX idx_member_phone (member_phone)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("储值提成表创建成功")


def get_store_id(conn, store_name_raw):
    store_name = simplify_store_name(store_name_raw)
    if not store_name:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
    conn.commit()
    return cursor.lastrowid


def import_stored_commission_files(file_paths):
    create_stored_commission_table()

    conn = get_conn()
    cursor = conn.cursor()

    total_count = 0

    for file_path in file_paths:
        print(f"\n导入文件: {Path(file_path).name}")
        df = pd.read_excel(file_path)
        print(f"  总行数: {len(df)}")

        # 删除该文件日期范围内的数据，避免重复
        dates_to_delete = set()
        for _, row in df.iterrows():
            dv = row.get('营业日')
            if pd.notna(dv):
                try:
                    dates_to_delete.add(pd.to_datetime(dv).strftime('%Y-%m-%d'))
                except:
                    pass
        for ds in dates_to_delete:
            cursor.execute("DELETE FROM stored_commission WHERE business_date = %s", (ds,))
        conn.commit()

        count = 0
        for _, row in df.iterrows():
            try:
                store_name_raw = str(row.get('门店', ''))
                store_id = get_store_id(conn, store_name_raw)
                if not store_id:
                    continue

                business_date = None
                dv = row.get('营业日')
                if pd.notna(dv):
                    try:
                        business_date = pd.to_datetime(dv).strftime('%Y-%m-%d')
                    except:
                        pass

                stored_time = None
                st = row.get('储值时间')
                if pd.notna(st):
                    try:
                        stored_time = pd.to_datetime(st).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # 处理提成金额（去除"元"字）
                commission_amount_str = str(row.get('提成金额', 0))
                commission_amount = float(commission_amount_str.replace('元', '').strip()) if commission_amount_str else 0

                cursor.execute('''
                INSERT INTO stored_commission
                (store_id, business_date, stored_time, commission_staff, staff_account,
                 member_phone, stored_amount, commission_rule, commission_amount)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    store_id,
                    business_date,
                    stored_time,
                    str(row.get('提成人员', '')),
                    str(row.get('人员账号', '')),
                    str(row.get('会员手机号', '')),
                    float(row.get('储值金额', 0) or 0),
                    str(row.get('提成规则', '')),
                    commission_amount
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
    files = sorted(source_dir.glob("储值提成明细表*.xlsx"))

    if not files:
        print("未找到储值提成明细表*.xlsx 文件")
        return

    print("=" * 60)
    print(f"储值提成导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"找到 {len(files)} 个文件:")
    for f in files:
        print(f"  - {f.name}")

    import_stored_commission_files([str(f) for f in files])

    print("=" * 60)
    print("导入完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
