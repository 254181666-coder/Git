
#!/usr/bin/env python3
"""
查看 order_daily 表结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("🔍 查看 order_daily 表结构")
print("=" * 80)

# 查看表结构
df_structure = query("DESCRIBE order_daily")
print("\n表结构:")
for idx, row in df_structure.iterrows():
    print(f"  {row['Field']}: {row['Type']}")

# 查看一些数据
print("\n\n前10条数据:")
df = query("SELECT * FROM order_daily LIMIT 10")
print(df.to_string())

print("\n" + "=" * 80)
print("✅ 完成")
print("=" * 80)
