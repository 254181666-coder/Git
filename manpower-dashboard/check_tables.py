
"""
检查数据库中有哪些表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

print("=== 检查数据库中所有表...")
print()

# 检查表
sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
df = query(sql)
print("所有表:")
for i, row in df.iterrows():
    print(f"{i+1}. {row['name']}")

print()

# 查看每个表的前5条记录（简短）
for table_name in df['name']:
    try:
        sql = f"SELECT * FROM {table_name} LIMIT 5;"
        table_data = query(sql)
        print(f"\n=== {table_name} 表前5条 ===")
        print(table_data)
        print(f"  列名: {list(table_data.columns)}")
    except Exception as e:
        print(f"\n=== {table_name} 表无法读取: {e} ===")

