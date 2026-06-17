
"""
查找商品销售汇总相关表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 查找商品销售汇总相关表 ===\n")

sql = """
SHOW TABLES
"""

df = query(sql)
print("所有表:")
for table in df.iloc[:, 0]:
    if 'product' in table.lower() or 'sales' in table.lower() or '汇总' in table:
        print(f"  - {table}")

print(f"\n\n=== 查看所有表 ===\n")
for table in df.iloc[:, 0]:
    print(f"  - {table}")

