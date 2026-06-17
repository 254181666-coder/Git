#!/usr/bin/env python3
import pymysql
from datetime import datetime
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("=" * 80)
print("查询4月数据范围")
print("=" * 80)

stores = {1: '鸡西店', 8: '安达店', 11: '通化店'}

for store_id, store_name in stores.items():
    print(f"\n{store_name}:")
    
    # 查询4月上半月（1-15日）午夜场订单
    sql = """
    SELECT COUNT(*) as total, SUM(actual_amount) as amount
    FROM order_detail 
    WHERE store_id = %s 
    AND data_date BETWEEN '2026-04-01' AND '2026-04-15'
    AND HOUR(open_time) &gt;= 0 AND HOUR(open_time) &lt; 6
    """
    cursor.execute(sql, (store_id,))
    result1 = cursor.fetchone()
    
    print(f"4月上半月（1-15日）午夜场订单数: {result1['total']}, 金额: {result1['amount'] or 0}")
    
    # 查询4月下半月（16-30日）午夜场订单
    sql = """
    SELECT COUNT(*) as total, SUM(actual_amount) as amount
    FROM order_detail 
    WHERE store_id = %s 
    AND data_date BETWEEN '2026-04-16' AND '2026-04-30'
    AND HOUR(open_time) &gt;= 0 AND HOUR(open_time) &lt; 6
    """
    cursor.execute(sql, (store_id,))
    result2 = cursor.fetchone()
    
    print(f"4月下半月（16-30日）午夜场订单数: {result2['total']}, 金额: {result2['amount'] or 0}")

cursor.close()
conn.close()
