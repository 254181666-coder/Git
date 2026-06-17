#!/usr/bin/env python3
import sys
import re
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


def create_order_detail_table():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_detail (
        id INT AUTO_INCREMENT PRIMARY KEY,
        store_id INT NOT NULL,
        data_date DATE NOT NULL,
        time_period VARCHAR(50) DEFAULT '',
        room_type VARCHAR(50) DEFAULT '',
        order_type VARCHAR(50) DEFAULT '',
        room_no VARCHAR(50) DEFAULT '',
        open_time DATETIME DEFAULT NULL,
        close_time DATETIME DEFAULT NULL,
        customer_name VARCHAR(100) DEFAULT '',
        customer_phone VARCHAR(20) DEFAULT '',
        order_no VARCHAR(100) DEFAULT '',
        should_amount DECIMAL(12,2) DEFAULT 0,
        actual_amount DECIMAL(12,2) DEFAULT 0,
        room_fee DECIMAL(12,2) DEFAULT 0,
        product_fee DECIMAL(12,2) DEFAULT 0,
        source_channel VARCHAR(50) DEFAULT '',
        scene VARCHAR(50) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_store_id (store_id),
        INDEX idx_data_date (data_date),
        INDEX idx_time_period (time_period),
        INDEX idx_room_no (room_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')
    conn.commit()
    cursor.close()
    conn.close()
    print("订单明细表创建成功")


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


def import_order_files(file_paths):
    create_order_detail_table()

    conn = get_conn()
    cursor = conn.cursor()

    # 第一步：先收集所有文件中涉及的日期
    all_dates = set()
    for file_path in file_paths:
        df = pd.read_csv(file_path, encoding='gbk', nrows=10000)
        if '开房时间' in df.columns:
            for t in df['开房时间'].dropna():
                try:
                    dt = pd.to_datetime(t)
                    all_dates.add(dt.date())
                except:
                    pass

    # 第二步：删除这些日期的旧数据
    if all_dates:
        date_strs = [str(d) for d in all_dates]
        placeholders = ','.join(['%s'] * len(date_strs))
        cursor.execute(f"DELETE FROM order_detail WHERE data_date IN ({placeholders})", date_strs)
        conn.commit()
        print(f"\n已删除旧数据: {len(date_strs)} 个日期, {cursor.rowcount} 条记录")

    total_count = 0

    for file_path in file_paths:
        print(f"\n导入文件: {Path(file_path).name}")
        df = pd.read_csv(file_path, encoding='gbk')
        print(f"  总行数: {len(df)}")

        cols = df.columns.tolist()
        print(f"  关键列检查:")
        key_cols = ['门店', '开房时段', '开房类型', '包厢号', '开房时间', '关房时间',
                    '开房人姓名', '开房人手机号', '开台单号', '应收金额', '实收金额', '房费收入', '商品收入', '来源渠道', '场景']
        for col in key_cols:
            if col in cols:
                print(f"    ✓ {col}")
            else:
                print(f"    ✗ {col} (未找到)")

        count = 0
        for _, row in df.iterrows():
            try:
                store_name_raw = str(row.get('门店', ''))
                store_id = get_store_id(conn, store_name_raw)
                if not store_id:
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

                # 根据开房时间计算时段
                if open_time:
                    hour = open_time.hour
                    if 9 <= hour < 18:
                        time_period = '日场'
                    elif 18 <= hour < 24:
                        time_period = '晚场'
                    else:  # 0-9
                        time_period = '午夜场'
                else:
                    time_period = ''

                room_fee = float(row.get('房费收入', 0) or 0)
                product_fee = float(row.get('商品收入', 0) or 0)

                cursor.execute('''
                INSERT INTO order_detail
                (store_id, data_date, time_period, room_type, order_type, room_no,
                 open_time, close_time, customer_name, customer_phone, order_no,
                 should_amount, actual_amount, room_fee, product_fee, source_channel, scene)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    store_id,
                    data_date,
                    time_period,
                    str(row.get('开房类型', '')),
                    str(row.get('订单类型', '')),
                    str(row.get('包厢号', '')),
                    open_time,
                    close_time,
                    str(row.get('开房人姓名', '')),
                    str(row.get('开房人手机号', '')),
                    str(row.get('开台单号', '')),
                    float(row.get('应收金额', 0) or 0),
                    float(row.get('实收金额', 0) or 0),
                    room_fee,
                    product_fee,
                    str(row.get('来源渠道', '')),
                    str(row.get('场景', ''))
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
    order_files = sorted(source_dir.glob("order_export_*.csv"))

    if not order_files:
        print("未找到 order_export_*.csv 文件")
        return

    print("=" * 60)
    print(f"订单明细导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"找到 {len(order_files)} 个文件:")
    for f in order_files:
        print(f"  - {f.name}")

    import_order_files([str(f) for f in order_files])

    print("=" * 60)
    print("导入完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
