#!/usr/bin/env python3
"""
检查order_daily表结构
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql


conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("检查order_daily表结构")
print("=" * 80)

cursor.execute("DESCRIBE order_daily")
rows = cursor.fetchall()
print("\n字段列表:")
for row in rows:
    print(f"  {row[0]}: {row[1]}")

# 看看time_period的实际长度
print("\n看看现在的time_period值:")
cursor.execute("SELECT DISTINCT time_period FROM order_daily LIMIT 20")
for row in cursor.fetchall():
    val = row[0]
    print(f"  '{val}' (length: {len(val) if val else 0})")

# 尝试更短的截断
print("\n尝试用更短的截断插入5月1日记录:")
cursor.execute("""
    SELECT store_id, data_date, time_period, order_type, source_channel
    FROM order_detail
    WHERE data_date = '2026-05-01'
""")
row = cursor.fetchone()
if row:
    store_id, data_date, time_period, order_type, source_channel = row
    
    cursor.execute("SELECT store_name FROM stores WHERE id = %s", (store_id,))
    store_result = cursor.fetchone()
    store_name = store_result[0] if store_result else '未知门店'
    
    is_group_buy = 1 if source_channel and '团购' in str(source_channel) else 0
    
    # 尝试更短的截断！
    if time_period:
        time_period = str(time_period)[:10]  # 只取前10个字符
    
    cursor.execute("""
        SELECT COUNT(*), SUM(actual_amount) FROM order_detail
        WHERE store_id = %s AND data_date = %s AND time_period = %s
        AND order_type = %s AND (source_channel LIKE '%%团购%%' OR %s = 0)
    """, (store_id, data_date, time_period, order_type, is_group_buy))
    count, revenue = cursor.fetchone()
    
    print(f"  截断后的time_period: '{time_period}'")
    
    try:
        cursor.execute("""
            INSERT INTO order_daily
            (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (data_date, store_name, store_name, time_period, order_type, is_group_buy, count, revenue or 0))
        conn.commit()
        print("\n✅ 成功插入!")
    except Exception as e:
        print(f"\n❌ 还是失败: {e}")
        
        # 最后尝试，直接用NULL或者空字符串
        print("\n尝试用NULL time_period:")
        try:
            cursor.execute("""
                INSERT INTO order_daily
                (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
                VALUES (%s, %s, %s, NULL, %s, %s, %s, %s)
            """, (data_date, store_name, store_name, order_type, is_group_buy, count, revenue or 0))
            conn.commit()
            print("✅ 成功用NULL插入!")
        except Exception as e2:
            print(f"❌ 还是失败: {e2}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
