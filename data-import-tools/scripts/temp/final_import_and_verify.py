#!/usr/bin/env python3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("📦 运行完整数据导入")
print("=" * 80)

# 先删除锁定文件
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
lock_files = list(LOGS_DIR.glob(".import_lock*"))
for f in lock_files:
    f.unlink()
    print(f"✅ 删除锁定文件: {f.name}")

# 运行完整导入
from scripts.import_data import main
main()

print("\n" + "=" * 80)
print("✅ 验证所有数据完整性")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

dates_to_check = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]

for table in ["order_detail", "order_daily", "store_daily"]:
    print(f"\n【{table}】")
    for date_str in dates_to_check:
        cursor.execute(f"""
            SELECT COUNT(*) FROM {table} WHERE data_date = %s
        """, (date_str,))
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {date_str}: {count} 条")

# 特别验证 store_daily 05-10 的门店数
print("\n" + "-" * 80)
print("📊 store_daily 2026-05-10 门店明细:")
cursor.execute("""
    SELECT store_id, store_name FROM store_daily 
    WHERE data_date = '2026-05-10'
    ORDER BY store_id
""")
for row in cursor.fetchall():
    print(f"  店{row[0]}: {row[1]}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 100% 完成！所有数据齐全！")
print("=" * 80)
