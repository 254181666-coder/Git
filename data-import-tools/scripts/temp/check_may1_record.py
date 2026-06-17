#!/usr/bin/env python3
"""
检查5月1日的那条记录
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql


conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("检查5月1日的记录")
print("=" * 80)

cursor.execute("SELECT * FROM order_detail WHERE data_date = '2026-05-01'")
row = cursor.fetchone()

if row:
    # 获取列名
    cursor.execute("DESCRIBE order_detail")
    columns = [col[0] for col in cursor.fetchall()]
    
    print("\n完整记录:")
    for i, col in enumerate(columns):
        print(f"  {col}: {row[i]}")
    
    print("\n" + "-" * 80)
    print("重点字段:")
    print(f"  time_period: {row[columns.index('time_period')]}")
    print(f"  order_type: {row[columns.index('order_type')]}")
    print(f"  source_channel: {row[columns.index('source_channel')]}")
    print(f"  actual_amount: {row[columns.index('actual_amount')]}")
    
    # 尝试手动插入这条记录
    print("\n尝试手动插入这条记录:")
    store_id = row[columns.index('store_id')]
    data_date = row[columns.index('data_date')]
    time_period = row[columns.index('time_period')]
    order_type = row[columns.index('order_type')]
    source_channel = row[columns.index('source_channel')]
    
    cursor.execute("SELECT store_name FROM stores WHERE id = %s", (store_id,))
    store_name = cursor.fetchone()[0] if cursor.fetchone() else ''
    
    is_group_buy = 1 if source_channel and '团购' in str(source_channel) else 0
    
    if time_period:
        time_period = str(time_period)[:50]
    
    # 检查这条记录会不会导致问题
    try:
        cursor.execute("""
            SELECT COUNT(*), SUM(actual_amount) FROM order_detail
            WHERE store_id = %s AND data_date = %s AND time_period = %s
            AND order_type = %s AND (source_channel LIKE '%%团购%%' OR %s = 0)
        """, (store_id, data_date, time_period, order_type, is_group_buy))
        count, revenue = cursor.fetchone()
        print(f"  符合条件的记录数: {count}, 总金额: {revenue}")
        
        # 尝试插入
        cursor.execute("""
            INSERT INTO order_daily
            (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (data_date, store_name, store_name, time_period, order_type, is_group_buy, count, revenue or 0))
        conn.commit()
        print(f"  ✅ 成功插入!")
    except Exception as e:
        print(f"  ❌ 失败: {e}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("完成")
print("=" * 80)
