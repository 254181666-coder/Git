#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='CHANGE_ME_MYSQL_PASSWORD', 
    database='ktv_analysis', 
    charset='utf8mb4'
)

try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT store_id, data_date, customers FROM store_daily LIMIT 20")
        results = cursor.fetchall()
        print("store_daily表中的示例数据:")
        for row in results:
            print(f"  store_id: {row[0]}, data_date: '{row[1]}', customers: {row[2]}")

finally:
    conn.close()
