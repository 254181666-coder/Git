"""测试数据库连接"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import query, get_engine
from src.config import USE_MYSQL

print(f"USE_MYSQL = {USE_MYSQL}")

print(f"\n测试数据库连接...")
engine = get_engine()
print(f"引擎: {engine}")

print(f"\n检查有哪些表...")
if USE_MYSQL:
    tables = query("SHOW TABLES")
else:
    tables = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print(tables)

print(f"\n检查 order_daily 表是否存在...")
try:
    order_data = query("SELECT COUNT(*) as cnt FROM order_daily")
    print(f"✅ order_daily 表有 {order_data.iloc[0,0]} 条记录")
    if order_data.iloc[0,0] > 0:
        print("\norder_daily 表预览:")
        sample = query("SELECT * FROM order_daily LIMIT 5")
        print(sample)
except Exception as e:
    print(f"❌ order_daily 表不存在或查询失败: {e}")

print(f"\n检查 store_daily 表...")
store_data = query("SELECT COUNT(*) as cnt FROM store_daily")
print(f"store_daily 表有 {store_data.iloc[0,0]} 条记录")

print("\n✅ 数据库检查完成！")
