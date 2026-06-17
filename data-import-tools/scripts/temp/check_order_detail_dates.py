
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

def main():
    print("=" * 80)
    print("检查 order_detail 表中的日期分布")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 检查最近10天的数据量
    cursor.execute('''
    SELECT data_date, COUNT(*) as count
    FROM order_detail
    WHERE data_date >= '2026-04-20'
    GROUP BY data_date
    ORDER BY data_date DESC
    ''')
    
    print("\n📅 order_detail 表最近日期数据:")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 条记录")
    
    # 专门检查5月2日的数据，看看是不是真的
    print("\n🔍 检查 2026-05-02 的数据详情:")
    cursor.execute('''
    SELECT COUNT(*), MIN(open_time), MAX(open_time)
    FROM order_detail
    WHERE data_date = '2026-05-02'
    ''')
    count, min_time, max_time = cursor.fetchone()
    
    print(f"   记录数: {count}")
    print(f"   最早开房时间: {min_time}")
    print(f"   最晚开房时间: {max_time}")
    
    # 看看实际文件内容
    print("\n📂 检查 source 目录下的文件:")
    source_dir = Path(PROJECT_ROOT) / "data" / "source"
    
    for f in sorted(source_dir.glob("order_export*")):
        print(f"   {f.name}")
    
    # 检查归档目录下的文件
    print("\n📦 检查归档目录下的文件:")
    archive_dir = Path(PROJECT_ROOT) / "data" / "archive"
    
    for f in sorted(archive_dir.glob("source_2026-05-*")):
        if f.is_dir():
            for ff in sorted(f.glob("order_export*")):
                print(f"   {f.name}/{ff.name}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

