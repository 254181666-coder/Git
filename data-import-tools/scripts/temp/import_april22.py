#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

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

def main():
    print("=" * 80)
    print("导入 4月22日 order 数据")
    print("=" * 80)
    
    file_path = PROJECT_ROOT / "data" / "source" / "order_export_19744_20260429135505.csv"
    
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return
    
    df = pd.read_csv(file_path, encoding='gbk')
    print(f"文件行数: {len(df)}")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    print("\n删除旧数据...")
    cursor.execute("DELETE FROM order_detail WHERE data_date = '2026-04-22'")
    del_count = cursor.rowcount
    conn.commit()
    print(f"删除了 {del_count} 条旧数据")
    
    print("\n开始导入...")
    count = 0
    for idx, row in df.iterrows():
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
            
            time_period = ''
            if open_time:
                hour = open_time.hour
                if 9 <= hour < 18:
                    time_period = '日场'
                elif 18 <= hour < 24:
                    time_period = '晚场'
                else:
                    time_period = '午夜场'
            
            room_fee = float(row.get('房费收入', 0) or 0)
            product_fee = float(row.get('商品收入', 0) or 0)
            
            cursor.execute("""
                INSERT INTO order_detail
                (store_id, data_date, time_period, room_type, order_type, room_no,
                 open_time, close_time, customer_name, customer_phone, order_no,
                 should_amount, actual_amount, room_fee, product_fee, source_channel, scene)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
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
    cursor.close()
    conn.close()
    
    print(f"\n✅ 成功导入 {count} 条记录！")
    
    print("\n验证数据：")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM order_detail WHERE data_date = '2026-04-22'")
    cnt = cursor.fetchone()[0]
    print(f"  2026-04-22 总记录数: {cnt}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
