#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("检查 store_daily 表中的日期：")
print("-" * 60)

cursor.execute("""
    SELECT data_date, COUNT(*) as store_count, SUM(total_revenue) as total_revenue
    FROM store_daily
    WHERE data_date >= '2026-05-10'
    GROUP BY data_date
    ORDER BY data_date
""")
rows = cursor.fetchall()

for row in rows:
    print(f"{row['data_date']}: {row['store_count']} 家店，总营业额 {row['total_revenue']:.2f}")

# 检查 5月13日
print("\n5月13日详细数据：")
cursor.execute("""
    SELECT s.store_name, sd.total_revenue
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE sd.data_date = '2026-05-13'
    ORDER BY s.store_name
""")
may13 = cursor.fetchall()

if may13:
    for row in may13:
        print(f"  {row['store_name']}: {row['total_revenue']:.2f}")
else:
    print("  没有数据！")

# 检查下载文件夹里的日营业数据文件
downloads_dir = Path("/Users/ann/Downloads")
daily_files = [f for f in downloads_dir.glob("日营业数据表*.xlsx")]
print("\n检查下载文件夹里的日营业数据文件内容：")
for f in daily_files:
    print(f"\n{f.name}:")
    try:
        df = pd.read_excel(f)
        if '日期' in df.columns:
            dates = df['日期'].dropna()
            if len(dates) > 0:
                file_date = dates.iloc[0]
                print(f"  文件日期：{file_date}")
                if '门店' in df.columns:
                    stores = df['门店'].dropna()
                    print(f"  门店数量：{len(stores)}")
    except Exception as e:
        print(f"  读取失败：{e}")

cursor.close()
conn.close()
