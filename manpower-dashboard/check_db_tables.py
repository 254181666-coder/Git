
#!/usr/bin/env python3
"""
检查数据库中的所有表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查数据库中所有表")
print("=" * 80)

sql_tables = "SHOW TABLES"
df_tables = query(sql_tables)
print("\n数据库表列表：")
for i, row in df_tables.iterrows():
    print(f"  - {row[0]}")

print("\n\n检查商品销售相关表的数据：")
tables_to_check = [
    'product_sales',
    'product_sales_detail',
    'product_sales_log',
    'sales_detail',
    'sales_data',
    '商品销售明细',
    '商品销售汇总',
    'product_sales_summary',
    'order_product',
    'order_detail'
]

for table in tables_to_check:
    try:
        sql_count = f"SELECT COUNT(*) FROM {table}"
        sql_example = f"SELECT * FROM {table} LIMIT 5"

        count_result = query(sql_count)
        total_count = count_result.iloc[0, 0]

        print(f"\n=== {table} ===")
        print(f"总记录数: {total_count}")

        if total_count > 0:
            df_sample = query(sql_example)
            print("\n样例数据:")
            print(df_sample.head().to_string())

    except Exception as e:
        print(f"\n=== {table} ===")
        print(f"错误: {e}")
        continue

print("\n" + "=" * 80)
