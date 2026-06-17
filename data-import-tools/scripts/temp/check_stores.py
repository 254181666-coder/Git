
#!/usr/bin/env python3
import pymysql
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("=" * 60)
print("门店信息查询")
print("=" * 60)
cursor.execute("SELECT * FROM stores")
stores = cursor.fetchall()
for store in stores:
    print(f"门店ID: {store['id']}, 门店名称: {store['store_name']}")

print("\n" + "=" * 60)
print("数据日期范围")
print("=" * 60)
cursor.execute("SELECT MIN(data_date) as min_date, MAX(data_date) as max_date FROM order_detail")
date_range = cursor.fetchone()
print(f"最早日期: {date_range['min_date']}")
print(f"最晚日期: {date_range['max_date']}")

cursor.close()
conn.close()
