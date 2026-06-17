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
    print("检查Order文件与数据库的差异")
    print("=" * 80)
    
    source_dir = PROJECT_ROOT / "data" / "source"
    all_order_files = sorted(source_dir.glob("order_export_*.csv"))
    
    print(f"\nsource目录中有 {len(all_order_files)} 个order文件:")
    
    file_info = []
    for f in all_order_files:
        df_sample = pd.read_csv(f, encoding='gbk', nrows=100)
        unique_dates = set()
        if '开房时间' in df_sample.columns:
            for t in df_sample['开房时间'].dropna():
                try:
                    dt = pd.to_datetime(t)
                    unique_dates.add(dt.date())
                except:
                    pass
        file_info.append({
            'file': f,
            'name': f.name,
            'size_mb': f.stat().st_size / 1024 / 1024,
            'dates': unique_dates
        })
    
    print("\n文件详情:")
    for info in file_info:
        date_strs = [str(d) for d in sorted(info['dates'])]
        print(f"  {info['name']:<40} {info['size_mb']:.1f} MB, 日期: {', '.join(date_strs)}")
    
    print("\n" + "=" * 80)
    print("数据库中已有数据的日期:")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT DATE(data_date) as dt
        FROM order_detail
        ORDER BY dt DESC
    """)
    db_dates = [row[0] for row in cursor.fetchall()]
    print(f"\n数据库中共 {len(db_dates)} 个日期:")
    print(f"  最新日期: {db_dates[0] if db_dates else '无'}")
    print(f"  最早日期: {db_dates[-1] if db_dates else '无'}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("需要补充导入的日期:")
    print("=" * 80)
    
    all_file_dates = set()
    for info in file_info:
        all_file_dates.update(info['dates'])
    all_file_dates = sorted(all_file_dates, reverse=True)
    
    db_dates_set = set(db_dates)
    missing = [d for d in all_file_dates if d not in db_dates_set]
    if missing:
        print(f"\n缺少 {len(missing)} 个日期:")
        for d in sorted(missing):
            print(f"  - {d}")
    else:
        print("\n所有日期都已导入！")

if __name__ == "__main__":
    main()
