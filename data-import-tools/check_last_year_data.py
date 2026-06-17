#!/usr/bin/env python3
import sys
from pathlib import Path
import pymysql
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("📊 检查数据库中的数据年份...\n")

# 查看所有门店
cursor.execute("SELECT id, store_name FROM stores ORDER BY id")
stores = cursor.fetchall()
print(f"门店列表:")
for s in stores:
    print(f"  {s['id']}. {s['store_name']}")

# 查看数据日期范围
print(f"\n数据日期范围:")
cursor.execute("""
    SELECT 
        MIN(data_date) as min_date,
        MAX(data_date) as max_date,
        COUNT(DISTINCT data_date) as date_count
    FROM store_daily
""")
date_range = cursor.fetchone()
print(f"  从: {date_range['min_date']}")
print(f"  到: {date_range['max_date']}")
print(f"  共: {date_range['date_count']} 天数据")

# 查看上东店的数据
print(f"\n📌 上东店数据:")
cursor.execute("""
    SELECT 
        YEAR(data_date) as year,
        MONTH(data_date) as month,
        COUNT(*) as days,
        SUM(total_revenue) as total_revenue
    FROM store_daily
    WHERE store_id = (SELECT id FROM stores WHERE store_name = '上东店')
    GROUP BY YEAR(data_date), MONTH(data_date)
    ORDER BY year, month
""")
shangdong_data = cursor.fetchall()
for d in shangdong_data:
    print(f"  {d['year']}年{d['month']}月: {d['days']}天, ¥{d['total_revenue']:,.0f}")

# 查看晨宇店的数据
print(f"\n📌 晨宇店数据:")
cursor.execute("""
    SELECT 
        YEAR(data_date) as year,
        MONTH(data_date) as month,
        COUNT(*) as days,
        SUM(total_revenue) as total_revenue
    FROM store_daily
    WHERE store_id = (SELECT id FROM stores WHERE store_name = '晨宇店')
    GROUP BY YEAR(data_date), MONTH(data_date)
    ORDER BY year, month
""")
chenyu_data = cursor.fetchall()
for d in chenyu_data:
    print(f"  {d['year']}年{d['month']}月: {d['days']}天, ¥{d['total_revenue']:,.0f}")

cursor.close()
conn.close()
