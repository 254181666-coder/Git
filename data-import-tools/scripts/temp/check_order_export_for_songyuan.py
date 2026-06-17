#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE = PROJECT_ROOT / "data" / "source"

print("=" * 80)
print("检查 5月5-6号 order_export 中的门店")
print("=" * 80)

order_files = sorted(list(SOURCE.glob("order_export*.csv")))

for f in order_files:
    print(f"\n{f.name}:")
    try:
        df = pd.read_csv(f, encoding='gbk')
        if "门店名称" in df.columns:
            stores = df["门店名称"].dropna().unique()
            print(f"  门店: {sorted(stores)}")
        elif "门店" in df.columns:
            stores = df["门店"].dropna().unique()
            print(f"  门店: {sorted(stores)}")
        elif "开房时间" in df.columns:
            # 看一下
            print(f"  列名: {list(df.columns)}")
    except Exception as e:
        print(f"  错误: {e}")

print("\n" + "=" * 80)
print("检查数据库中 order_detail 表最近日期的门店")
print("=" * 80)

import sys
sys.path.insert(0, str(PROJECT_ROOT))
from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT data_date, store_id, COUNT(*) 
    FROM order_detail 
    WHERE data_date >= '2026-05-05'
    GROUP BY data_date, store_id
    ORDER BY data_date, store_id
""")

for row in cursor.fetchall():
    print(f"  {row[0]} 店 {row[1]}: {row[2]} 单")

cursor.close()
conn.close()

print("\n" + "=" * 80)
