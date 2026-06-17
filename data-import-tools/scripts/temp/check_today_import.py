#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

print("=" * 80)
print("📋 检查今天（2026-05-10）的数据导入状态")
print("=" * 80)

# 1. 检查 data/source 目录
print("\n📂 1. data/source 目录内容:")
print("-" * 80)
if SOURCE_DIR.exists():
    files = sorted([f for f in SOURCE_DIR.iterdir() if not f.name.startswith('.')])
    print(f"当前共 {len(files)} 个文件:")
    for f in files:
        size = f.stat().st_size
        print(f"  - {f.name} ({size} bytes)")
else:
    print("❌ source 目录不存在！")

# 2. 检查数据库各表
print("\n" + "=" * 80)
print("📊 2. 数据库各表检查:")
print("=" * 80)

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

# 检查日期范围
dates_to_check = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]

tables_to_check = ["order_detail", "store_daily", "order_daily"]

for table in tables_to_check:
    print(f"\n【{table}】")
    print("-" * 80)
    
    # 获取列名
    cursor.execute(f"DESCRIBE {table}")
    columns = [col[0] for col in cursor.fetchall()]
    
    # 找日期字段
    date_field = None
    for col in columns:
        if "date" in col.lower() and "create" not in col.lower() and "update" not in col.lower():
            date_field = col
            break
    
    if date_field:
        # 按日期查询
        for date_str in dates_to_check:
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {table} 
                    WHERE {date_field} = %s
                """, (date_str,))
                count = cursor.fetchone()[0]
                
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {date_str}: {count} 条")
            except Exception as e:
                print(f"  ⚠️  {date_str}: 查询失败 - {e}")
    
    # 检查 store_daily 或 order_daily 的午夜场
    if table == "order_daily" and date_field:
        print("\n  🕛 午夜场数据:")
        for date_str in dates_to_check:
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {table} 
                    WHERE {date_field} = %s AND time_period = '午夜场'
                """, (date_str,))
                count = cursor.fetchone()[0]
                status = "✅" if count > 0 else "❌"
                print(f"    {status} {date_str}: {count} 条")
            except Exception as e:
                print(f"    ⚠️  {date_str}: 查询失败 - {e}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("✅ 检查完成！")
print("=" * 80)
