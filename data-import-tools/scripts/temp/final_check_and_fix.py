#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

print("=" * 80)
print("检查 stored_commission 和 product_commission 表的 5 月份数据")
print("=" * 80)

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

for table in ['stored_commission', 'product_commission']:
    print(f"\n【{table}】")
    print("-" * 80)
    
    try:
        cursor.execute(f"""
            SELECT 
                MIN(business_date) AS min_date, 
                MAX(business_date) AS max_date, 
                COUNT(*) AS total_count
            FROM {table}
        """)
        min_date, max_date, total_count = cursor.fetchone()
        
        print(f"总记录数: {total_count}")
        print(f"日期范围: {min_date} 至 {max_date}")
        
        print("\n5 月份数据统计:")
        cursor.execute(f"""
            SELECT business_date, COUNT(*) AS count
            FROM {table}
            WHERE business_date >= '2026-05-01'
            GROUP BY business_date
            ORDER BY business_date
        """)
        
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} 条")
            
    except Exception as e:
        print(f"  ✗ 错误: {e}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("检查项目根目录是否有乱码文件名")
print("=" * 80)

import os
all_files = list(PROJECT_ROOT.iterdir())
print(f"\n项目根目录共有 {len(all_files)} 个文件:")

for f in all_files:
    # 检查文件名编码
    try:
        f.name.encode('utf-8')
    except:
        print(f"⚠️ 有乱码的文件: {f.name}")

print("\n" + "=" * 80)
print("检查是否有 source_history 里 5 月的提成文件还没导入?")
print("=" * 80)

SOURCE_HISTORY = PROJECT_ROOT / "data" / "archive" / "source_history"
if SOURCE_HISTORY.exists():
    # 找 5 月的提成文件
    commission_files = sorted(list(SOURCE_HISTORY.glob("*提成*.xlsx")))
    balance_files = sorted(list(SOURCE_HISTORY.glob("*会员余额*.xlsx")))
    
    print(f"\n找到储值提成文件: {len(commission_files)}")
    for f in commission_files[-10:]:
        print(f"  - {f.name}")
        
    print(f"\n找到会员余额文件: {len(balance_files)}")
    for f in balance_files[-10:]:
        print(f"  - {f.name}")
        
print("\n" + "=" * 80)
print("检查 data/source 目录当前有哪些文件:")
print("=" * 80)

SOURCE = PROJECT_ROOT / "data" / "source"
if SOURCE.exists():
    for f in sorted(list(SOURCE.iterdir())):
        if not f.name.startswith('.'):
            print(f"  - {f.name}")

print("\n" + "=" * 80)
print("最后检查 daily_import_with_archive.py 是否还在调用 daily_archive:")
print("=" * 80)

with open(PROJECT_ROOT / "scripts" / "daily_import_with_archive.py", encoding='utf-8') as f:
    print(f.read()[:800])

print("\n" + "=" * 80)
print("✅ 检查完成!")
print("=" * 80)
