
"""
检查product_sales表和v_store_summary视图
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import query

# 设置为使用MySQL
os.environ['USE_MYSQL'] = 'true'

print("=== 检查product_sales表日期分布 ===\n")

sql = """
SELECT ps.data_date, COUNT(*) as count, SUM(ps.quantity) as total_qty
FROM product_sales ps
GROUP BY ps.data_date
ORDER BY ps.data_date DESC
LIMIT 15
"""

df = query(sql)
print(df)

print(f"\n\n=== 查看v_store_summary视图 ===\n")
try:
    sql2 = "DESCRIBE v_store_summary"
    df2 = query(sql2)
    print(df2)
    
    print(f"\n--- v_store_summary 前5条数据 ---\n")
    sql3 = "SELECT * FROM v_store_summary LIMIT 5"
    df3 = query(sql3)
    print(df3)
except Exception as e:
    print(f"错误: {e}")

