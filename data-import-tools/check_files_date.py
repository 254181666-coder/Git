#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

# 检查数据库最新日期
conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()
cursor.execute("SELECT MAX(data_date) as max_date FROM store_daily")
max_date = cursor.fetchone()[0]
print(f"数据库最新日期：{max_date}")

# 检查下载文件夹里的日营业数据文件
downloads_dir = Path("/Users/ann/Downloads")
daily_files = list(downloads_dir.glob("日营业数据表*.xlsx"))
print(f"\n下载文件夹里的日营业数据文件：")
for f in daily_files:
    print(f"  - {f.name}")
    try:
        df = pd.read_excel(f)
        if '日期' in df.columns:
            dates = df['日期'].dropna()
            if len(dates) > 0:
                print(f"    文件包含日期：{dates.iloc[0]}")
    except Exception as e:
        print(f"    读取失败：{e}")

# 检查商品销售文件
print(f"\n商品销售文件：")
product_files = list(downloads_dir.glob("商品销售*.xlsx"))
for f in product_files:
    print(f"  - {f.name}")

cursor.close()
conn.close()
