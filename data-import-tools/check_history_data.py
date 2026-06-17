#!/usr/bin/env python3
import sys
from pathlib import Path
import pymysql
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)

# 查询晨宇店可用数据范围
query = """
SELECT MIN(data_date) as min_date, MAX(data_date) as max_date, COUNT(DISTINCT data_date) as days
FROM store_daily 
WHERE store_id = (SELECT id FROM stores WHERE store_name = '晨宇店')
"""

df_range = pd.read_sql(query, conn)
print("晨宇店数据范围：")
print(df_range)

# 查询2025年数据是否存在
query_2025 = """
SELECT data_date, weekday, customers_before_18, customers_18_to_24, customers_after_00, customers
FROM store_daily 
WHERE store_id = (SELECT id FROM stores WHERE store_name = '晨宇店')
AND data_date BETWEEN '2025-04-01' AND '2025-05-31'
ORDER BY data_date
"""

df_2025 = pd.read_sql(query_2025, conn)
print(f"\n2025年数据天数：{len(df_2025)}")

conn.close()
print("\n查询完成！")