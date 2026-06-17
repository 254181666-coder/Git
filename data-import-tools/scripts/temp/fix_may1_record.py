#!/usr/bin/env python3
"""
修复5月1日记录，不管有没有store，都插入order_daily
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
print("修复5月1日的记录")
print("=" * 80)

# 找到那条记录
cursor.execute("""
    SELECT store_id, data_date, time_period, order_type, source_channel
    FROM order_detail
    WHERE data_date = '2026-05-01'
""")
row = cursor.fetchone()

if row:
    store_id, data_date, time_period, order_type, source_channel = row
    
    # 获取门店名
    cursor.execute("SELECT store_name FROM stores WHERE id = %s", (store_id,))
    store_result = cursor.fetchone()
    store_name = store_result[0] if store_result else '未知门店'
    
    is_group_buy = 1 if source_channel and '团购' in str(source_channel) else 0
    
    # 处理time_period
    if time_period:
        time_period = str(time_period)[:50]
    
    # 汇总数据
    cursor.execute("""
        SELECT COUNT(*), SUM(actual_amount) FROM order_detail
        WHERE store_id = %s AND data_date = %s AND time_period = %s
        AND order_type = %s AND (source_channel LIKE '%%团购%%' OR %s = 0)
    """, (store_id, data_date, time_period, order_type, is_group_buy))
    count, revenue = cursor.fetchone()
    
    print(f"  store_id: {store_id}")
    print(f"  store_name: {store_name}")
    print(f"  data_date: {data_date}")
    print(f"  time_period: {time_period}")
    print(f"  order_type: {order_type}")
    print(f"  count: {count}")
    print(f"  revenue: {revenue}")
    
    # 插入order_daily
    try:
        cursor.execute("""
            INSERT INTO order_daily
            (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (data_date, store_name, store_name, time_period, order_type, is_group_buy, count, revenue or 0))
        conn.commit()
        print("\n✅ 成功插入5月1日的记录!")
    except Exception as e:
        print(f"\n❌ 失败: {e}")

# 验证结果
print("\n" + "-" * 80)
print("验证order_daily表现在包含5月1日:")
cursor.execute("SELECT * FROM order_daily WHERE data_date = '2026-05-01'")
result = cursor.fetchone()
if result:
    print(f"✅ 存在！记录为: {result}")
else:
    print("❌ 不存在")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("完成")
print("=" * 80)
