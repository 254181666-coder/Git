
#!/usr/bin/env python3
"""
检查新的商品销售表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("检查新表：product_sales_summary 和 product_sales_detail")
print("=" * 80)

tables = ['product_sales_summary', 'product_sales_detail']

for table_name in tables:
    try:
        print(f"\n{'='*80}")
        print(f"表：{table_name}")
        print(f"{'='*80}")
        
        # 检查表是否存在
        sql_check = f"SELECT COUNT(*) FROM {table_name}"
        count_result = query(sql_check)
        total_count = count_result.iloc[0, 0]
        print(f"总记录数：{total_count}")
        
        if total_count > 0:
            # 查看表结构
            sql_describe = f"DESCRIBE {table_name}"
            df_describe = query(sql_describe)
            print("\n表结构：")
            print(df_describe.to_string())
            
            # 查看样例数据
            sql_sample = f"SELECT * FROM {table_name} LIMIT 10"
            df_sample = query(sql_sample)
            print("\n样例数据：")
            print(df_sample.head().to_string())
            
            # 查看日期范围
            sql_dates = f"""
            SELECT data_date, COUNT(*) as count
            FROM {table_name}
            GROUP BY data_date
            ORDER BY data_date DESC
            LIMIT 10
            """
            df_dates = query(sql_dates)
            print("\n日期分布：")
            print(df_dates.to_string())
            
    except Exception as e:
        print(f"\n表 {table_name} 不存在或查询失败：")
        print(f"  错误：{e}")

print("\n" + "=" * 80)
