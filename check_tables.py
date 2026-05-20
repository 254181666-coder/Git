
#!/usr/bin/env python3
"""
检查数据库表结构
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query

print("=" * 80)
print("检查数据库表结构")
print("=" * 80)

# 先查看有哪些表
tables = query("SHOW TABLES")
print(f"所有表:")
for table_name in tables.iloc[:, 0].tolist():
    print(f"  {table_name}")

# 检查是否有日营业数据表
print("\n" + "=" * 80)
print("检查store_daily表")
print("=" * 80)

try:
    sd = query("DESCRIBE store_daily")
    print(f"store_daily表结构:")
    for _, row in sd.iterrows():
        print(f"  {row['Field']} ({row['Type']})")
except Exception as e:
    print(f"store_daily表不存在: {e}")

# 检查product_sales_detail表的结构，特别是是否有订单号关联
print("\n" + "=" * 80)
print("product_sales_detail表结构")
print("=" * 80)
psd = query("DESCRIBE product_sales_detail")
for _, row in psd.iterrows():
    print(f"  {row['Field']} ({row['Type']})")
