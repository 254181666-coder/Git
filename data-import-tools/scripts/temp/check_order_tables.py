#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def main():
    print("=" * 80)
    print("检查Order相关表数据完整性")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    print("\n1. 数据库中的Order相关表:")
    cursor.execute("SHOW TABLES LIKE '%order%'")
    order_tables = [row[0] for row in cursor.fetchall()]
    for t in order_tables:
        print(f"  - {t}")
    
    print("\n2. 检查 order_detail 表:")
    cursor.execute("DESCRIBE order_detail")
    print("  字段:")
    for col in cursor.fetchall():
        print(f"    {col[0]}")
    
    print("\n3. order_detail 按日期统计:")
    cursor.execute("""
        SELECT DATE(data_date) as dt, COUNT(*) as cnt
        FROM order_detail
        WHERE data_date IS NOT NULL
        GROUP BY DATE(data_date)
        ORDER BY dt DESC
    """)
    print("  日期\t\t记录数")
    print("  " + "-" * 30)
    total = 0
    for row in cursor.fetchall():
        print(f"  {row[0]}\t{row[1]}")
        total += row[1]
    print(f"\n  总计: {total} 条")
    
    print("\n4. order_detail 按门店统计:")
    cursor.execute("""
        SELECT s.store_name, COUNT(*) as cnt
        FROM order_detail od
        JOIN stores s ON od.store_id = s.id
        WHERE od.data_date >= '2026-04-01'
        GROUP BY s.store_name
        ORDER BY s.store_name
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条")
    
    print("\n5. order_daily 按日期统计:")
    cursor.execute("""
        SELECT data_date, COUNT(*) as cnt
        FROM order_daily
        GROUP BY data_date
        ORDER BY data_date DESC
    """)
    print("  日期\t\t记录数")
    print("  " + "-" * 30)
    for row in cursor.fetchall():
        print(f"  {row[0]}\t{row[1]}")
    
    print("\n" + "=" * 80)
    print("检查 source 目录中的order文件")
    print("=" * 80)
    
    source_dir = PROJECT_ROOT / "data" / "source"
    order_files = sorted(source_dir.glob("order_export_*.csv"))
    print(f"\n在 source 目录中找到 {len(order_files)} 个order文件:")
    for f in order_files:
        stat = f.stat()
        print(f"  {f.name:<40} ({stat.st_size // 1024} KB, {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')})")
    
    print("\n" + "=" * 80)
    print("检查 archive 目录中的order文件")
    print("=" * 80)
    
    archive_dir = PROJECT_ROOT / "data" / "archive"
    for day_dir in sorted(archive_dir.glob("source_2026_*"), reverse=True):
        if not day_dir.is_dir():
            continue
        day_order_files = sorted(day_dir.glob("order_export_*.csv"))
        if not day_order_files:
            continue
        print(f"\n{day_dir.name}:")
        for f in day_order_files:
            stat = f.stat()
            print(f"  {f.name:<40} ({stat.st_size // 1024} KB)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
