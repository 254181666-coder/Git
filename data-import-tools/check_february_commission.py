#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(host='localhost', port=3306, user='root', password='CHANGE_ME_MYSQL_PASSWORD', database='ktv_analysis', charset='utf8mb4')
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(*) as cnt, MIN(business_date) as min_date, MAX(business_date) as max_date 
    FROM product_commission 
    WHERE MONTH(business_date) = 2
""")
row = cursor.fetchone()
print(f"2月商品提成: 数量={row[0]}, 日期范围={row[1]} ~ {row[2]}")

cursor.execute("""
    SELECT COUNT(*) as cnt, MIN(business_date) as min_date, MAX(business_date) as max_date 
    FROM stored_commission 
    WHERE MONTH(business_date) = 2
""")
row = cursor.fetchone()
print(f"2月储值提成: 数量={row[0]}, 日期范围={row[1]} ~ {row[2]}")

cursor.execute("""
    SELECT YEAR(business_date) as year, COUNT(*) as cnt 
    FROM product_commission 
    WHERE MONTH(business_date) = 2 
    GROUP BY YEAR(business_date)
""")
print("\n商品提成按年份2月数据:")
for row in cursor.fetchall():
    print(f"  {row[0]}年: {row[1]}条")

cursor.execute("""
    SELECT YEAR(business_date) as year, COUNT(*) as cnt 
    FROM stored_commission 
    WHERE MONTH(business_date) = 2 
    GROUP BY YEAR(business_date)
""")
print("\n储值提成按年份2月数据:")
for row in cursor.fetchall():
    print(f"  {row[0]}年: {row[1]}条")

cursor.execute("SELECT MIN(business_date), MAX(business_date) FROM product_commission")
row = cursor.fetchone()
print(f"\n商品提成整体日期范围: {row[0]} ~ {row[1]}")

cursor.execute("SELECT MIN(business_date), MAX(business_date) FROM stored_commission")
row = cursor.fetchone()
print(f"储值提成整体日期范围: {row[0]} ~ {row[1]}")

# 查看2月具体数据样例
cursor.execute("""
    SELECT business_date, commission_staff, product, quantity, commission_amount 
    FROM product_commission 
    WHERE MONTH(business_date) = 2 
    LIMIT 5
""")
print("\n2月商品提成示例:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
