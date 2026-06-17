
"""
查找所有order相关的表并查看表结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 查找包含order的表 ===\n")

sql = """
SHOW TABLES LIKE '%order%'
"""

df = query(sql)
print("找到的order相关表:")
for table in df.iloc[:, 0]:
    print(f"  - {table}")

print(f"\n\n=== 查看每个表的结构 ===\n")
for table in df.iloc[:, 0]:
    try:
        sql2 = f"DESCRIBE {table}"
        df2 = query(sql2)
        print(f"\n--- {table} 结构: ---\n")
        print(df2)
        
        print(f"\n--- {table} 前5条数据 ---\n")
        sql3 = f"SELECT * FROM {table} LIMIT 5"
        df3 = query(sql3)
        print(df3)
    except Exception as e:
        print(f"\n--- {table} 错误: {e} ---\n")

