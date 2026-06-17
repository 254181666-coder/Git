#!/usr/bin/env python3
"""
导入商品提成数据到 product_commission 表
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


def create_product_commission_table():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_commission (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ref_no VARCHAR(100) DEFAULT '',
        store_id INT NOT NULL,
        business_date DATE NOT NULL,
        room VARCHAR(50) DEFAULT '',
        order_time DATETIME DEFAULT NULL,
        open_time DATETIME DEFAULT NULL,
        close_time DATETIME DEFAULT NULL,
        commission_staff VARCHAR(100) DEFAULT '',
        staff_account VARCHAR(100) DEFAULT '',
        product VARCHAR(200) DEFAULT '',
        quantity INT DEFAULT 0,
        paid_amount DECIMAL(12,2) DEFAULT 0,
        commission_method VARCHAR(100) DEFAULT '',
        commission_amount DECIMAL(12,2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_store_id (store_id),
        INDEX idx_business_date (business_date),
        INDEX idx_ref_no (ref_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("商品提成表创建成功")


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


def import_product_commission_files(file_paths):
    create_product_commission_table()

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
            cursor.execute("DELETE FROM product_commission WHERE business_date = %s", (ds,))
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

                order_time = None
                ot = row.get('点单时间')
                if pd.notna(ot):
                    try:
                        order_time = pd.to_datetime(ot).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                open_time = None
                opt = row.get('开房时间')
                if pd.notna(opt):
                    try:
                        open_time = pd.to_datetime(opt).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                close_time = None
                ct = row.get('关房时间')
                if pd.notna(ct):
                    try:
                        close_time = pd.to_datetime(ct).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # 处理提成金额（去除"元"字）
                commission_amount_str = str(row.get('提成金额', 0))
                commission_amount = float(commission_amount_str.replace('元', '').strip()) if commission_amount_str else 0

                cursor.execute('''
                INSERT INTO product_commission
                (ref_no, store_id, business_date, room, order_time, open_time, close_time,
                 commission_staff, staff_account, product, quantity, paid_amount,
                 commission_method, commission_amount)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    str(row.get('ref_no', '')),
                    store_id,
                    business_date,
                    str(row.get('包厢', '')),
                    order_time,
                    open_time,
                    close_time,
                    str(row.get('提成人员', '')),
                    str(row.get('人员账号', '')),
                    str(row.get('商品', '')),
                    int(row.get('数量', 0) or 0),
                    float(row.get('实付金额', 0) or 0),
                    str(row.get('提成方式', '')),
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
    files = sorted(source_dir.glob("商品提成明细表*.xlsx"))

    if not files:
        print("未找到商品提成明细表*.xlsx 文件")
        return

    print("=" * 60)
    print(f"商品提成导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"找到 {len(files)} 个文件:")
    for f in files:
        print(f"  - {f.name}")

    import_product_commission_files([str(f) for f in files])

    print("=" * 60)
    print("导入完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
