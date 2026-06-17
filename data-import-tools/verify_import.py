#!/usr/bin/env python3
import sys
from pathlib import Path
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("验证导入结果...\n")

print("2026年5月数据统计:")
cursor.execute("""
SELECT data_date, COUNT(*) as store_count, SUM(total_revenue) as total
FROM store_daily 
WHERE data_date BETWEEN '2026-05-01' AND '2026-05-13'
GROUP BY data_date
ORDER BY data_date
""")

for row in cursor.fetchall():
    print(f"  {row['data_date']}: {row['store_count']} 家门店, ¥{row['total']:.0f}")

print("\n\n上东店数据(5月1-13日):")
cursor.execute("""
SELECT data_date, total_revenue
FROM store_daily 
WHERE store_id = (SELECT id FROM stores WHERE store_name = '上东店')
AND data_date BETWEEN '2026-05-01' AND '2026-05-13'
ORDER BY data_date
""")
for row in cursor.fetchall():
    print(f"  {row['data_date']}: ¥{row['total_revenue']:.0f}")

print("\n\n晨宇店数据(5月1-13日):")
cursor.execute("""
SELECT data_date, total_revenue
FROM store_daily 
WHERE store_id = (SELECT id FROM stores WHERE store_name = '晨宇店')
AND data_date BETWEEN '2026-05-01' AND '2026-05-13'
ORDER BY data_date
""")
for row in cursor.fetchall():
    print(f"  {row['data_date']}: ¥{row['total_revenue']:.0f}")

cursor.close()
conn.close()

print("\n✅ 数据验证完成！")
