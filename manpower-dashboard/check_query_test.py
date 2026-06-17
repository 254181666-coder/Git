
#!/usr/bin/env python3
"""
测试 product_sales_detail 表是否有 big_category 字段
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查 product_sales_detail 是否有 big_category")
print("=" * 80)

sql = "SELECT big_category FROM product_sales_detail LIMIT 1"
try:
    df = query(sql)
    print("✅ 有 big_category 字段！")
except Exception as e:
    print(f"❌ 没有 big_category 字段！")
    print(f"   错误: {e}")
    print()
    print("检查一下 product_sales_summary 是否有 big_category")
    sql2 = "SELECT big_category FROM product_sales_summary LIMIT 1"
    try:
        df2 = query(sql2)
        print("✅ product_sales_summary 有 big_category 字段！")
        print(df2.to_string())
    except Exception as e2:
        print(f"❌ 也没有 big_category：{e2}")
