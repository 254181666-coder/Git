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
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")

        # 查看store_daily表的结构
        print("\nstore_daily表的列:")
        cursor.execute("DESCRIBE store_daily")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")

finally:
    conn.close()
