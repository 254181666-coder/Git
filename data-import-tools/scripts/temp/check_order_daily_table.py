
#!/usr/bin/env python3
"""
检查 order_daily 表
"""
import sys
from pathlib import Path
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

conn = get_conn()
cursor = conn.cursor()

print("检查数据库中的表：")
cursor.execute("SHOW TABLES")
tables = [t[0] for t in cursor.fetchall()]
for table in tables:
    print(f"  - {table}")

print(f"\n\n检查 order_daily 表是否存在：{'order_daily' in tables}")

if 'order_daily' in tables:
    print("\norder_daily 表的数据：")
    cursor.execute("SELECT COUNT(*) FROM order_daily")
    print(f"  总行数: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT DISTINCT time_period FROM order_daily LIMIT 10")
    print(f"  时段值: {[t[0] for t in cursor.fetchall()]}")
    
    cursor.execute("SELECT MIN(data_date), MAX(data_date) FROM order_daily")
    min_date, max_date = cursor.fetchone()
    print(f"  日期范围: {min_date} ~ {max_date}")

cursor.close()
conn.close()
