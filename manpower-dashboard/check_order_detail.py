
"""
检查order_detail表结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== order_detail表结构 ===\n")

sql = "DESCRIBE order_detail"
df = query(sql)
print(df)

print(f"\n--- order_detail前5条数据 ---\n")
sql2 = "SELECT * FROM order_detail LIMIT 5"
df2 = query(sql2)
print(df2)

print(f"\n--- 检查order_detail的日期范围 ---\n")
sql3 = "SELECT MIN(data_date) as min_date, MAX(data_date) as max_date, COUNT(*) as total FROM order_detail"
df3 = query(sql3)
print(df3)

