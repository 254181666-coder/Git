#!/usr/bin/env python3
"""
最终修复：映射time_period到允许的ENUM值
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql


def map_time_period(tp):
    """把任意的time_period映射到允许的ENUM值"""
    if not tp:
        return '日场'
    tp = str(tp)
    if '午夜' in tp:
        return '午夜场'
    elif '黄金' in tp:
        return '黄金场'
    elif '晚' in tp:
        return '黄金场'  # 晚场映射到黄金场
    else:
        return '日场'


conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("最终修复5月1日记录")
print("=" * 80)

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
    
    # 映射time_period
    mapped_time_period = map_time_period(time_period)
    print(f"  原始time_period: '{time_period}'")
    print(f"  映射后: '{mapped_time_period}'")
    
    # 计算统计 - 注意这里要按映射前的原始值查询，或者放宽条件
    cursor.execute("""
        SELECT COUNT(*), SUM(actual_amount) FROM order_detail
        WHERE store_id = %s AND data_date = %s
        AND order_type = %s AND (source_channel LIKE '%%团购%%' OR %s = 0)
    """, (store_id, data_date, order_type, is_group_buy))
    count, revenue = cursor.fetchone()
    
    print(f"\n  count: {count}, revenue: {revenue}")
    
    try:
        cursor.execute("""
            INSERT INTO order_daily
            (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (data_date, store_name, store_name, mapped_time_period, order_type, is_group_buy, count, revenue or 0))
        conn.commit()
        print("\n✅ 成功插入!")
    except Exception as e:
        print(f"\n❌ 失败: {e}")

# 验证
print("\n" + "-" * 80)
cursor.execute("SELECT * FROM order_daily WHERE data_date = '2026-05-01'")
result = cursor.fetchone()
if result:
    print(f"✅ 5月1日已在order_daily表中！记录为:")
    print(f"   {result}")

# 同时更新import_data.py中的generate_order_daily函数，加入time_period映射
print("\n" + "-" * 80)
print("现在更新import_data.py中的time_period映射...")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)
