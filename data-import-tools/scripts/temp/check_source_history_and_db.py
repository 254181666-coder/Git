#!/usr/bin/env python3
"""完整检查 source_history 中的所有文件以及数据库各表的情况"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

print("=" * 80)
print("📊 完整检查 source_history 和数据库各表")
print("=" * 80)

ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
SOURCE_HISTORY_DIR = ARCHIVE_DIR / "source_history"

print("\n1️⃣ 检查 source_history 里的所有文件：")
print("=" * 80)
all_files = sorted(SOURCE_HISTORY_DIR.glob("*"))
print(f"\nsource_history 共 {len(all_files)} 个文件：\n")

# 按类型统计
file_types = {
    'order_export': [],
    'card_detail': [],
    '储值订单': [],
    '储值提成': [],
    '商品提成': [],
    '会员余额': [],
    '商品销售明细': [],
    '商品销售汇总': [],
    '日营业数据': []
}

for f in all_files:
    for t in file_types.keys():
        if t in f.name:
            file_types[t].append(f)

for t, files in file_types.items():
    print(f"  {t:12s} : {len(files)} 个")
    for f in files[-5:]:
        print(f"    - {f.name}")

print("\n" + "=" * 80)
print("2️⃣ 检查数据库各表的5月数据：")
print("=" * 80)

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

# 检查的表列表
tables = [
    'order_detail',
    'order_daily',
    'stored_value',
    'stored_commission',
    'product_commission',
    'member_balance',
    'store_daily'
]

for table in tables:
    print(f"\n【{table}】")
    
    # 先检查表是否存在
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_date >= '2026-05-01'")
        count_may = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT MIN(data_date), MAX(data_date) FROM {table}")
        min_date, max_date = cursor.fetchone()
        
        print(f"   总记录数(5月)：{count_may}")
        print(f"   日期范围：{min_date} ~ {max_date}")
        
        if count_may >0:
            cursor.execute(f"""
                SELECT data_date, COUNT(*) 
                FROM {table} 
                WHERE data_date >= '2026-05-01'
                GROUP BY data_date
                ORDER BY data_date
            """)
            for row in cursor.fetchall():
                print(f"    {row[0]}: {row[1]} 条")
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
