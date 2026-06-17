#!/usr/bin/env python3
import pymysql
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=== 4月总记录数 ===")
cursor.execute("SELECT COUNT(*) FROM stored_value WHERE data_date >= '2026-04-01' AND data_date < '2026-05-01'")
print(cursor.fetchone()[0])

print("\n=== 每天记录数 ===")
cursor.execute("""
    SELECT DATE(data_date) as dt, COUNT(*) as cnt 
    FROM stored_value 
    WHERE data_date >= '2026-04-01' AND data_date < '2026-05-01' 
    GROUP BY dt 
    ORDER BY dt
""")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n=== 按门店统计 ===")
cursor.execute("""
    SELECT s.store_name, COUNT(*) as cnt 
    FROM stored_value v 
    JOIN stores s ON v.store_id = s.id 
    WHERE v.data_date >= '2026-04-01' AND v.data_date < '2026-05-01' 
    GROUP BY s.store_name
""")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

cursor.close()
conn.close()
