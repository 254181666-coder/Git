#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def main():
    print("=" * 80)
    print("检查商品销售汇总表的日期范围")
    print("=" * 80)
    
    file_path = PROJECT_ROOT / "data" / "source" / "商品销售汇总_2026_04_26.xlsx"
    
    if not file_path.exists():
        print("文件不存在")
        return
    
    df = pd.read_excel(file_path)
    
    print(f"\n文件总行数: {len(df)}")
    print(f"\n列: {df.columns.tolist()}")
    
    # 检查每个日期
    all_dates = set()
    for _, row in df.iterrows():
        date_str = str(row.get('日期', ''))
        if '~' in date_str:
            parts = date_str.split('~')
            for p in parts:
                if len(p) == 8:
                    ds = f"{p[:4]}-{p[4:6]}-{p[6:8]}"
                    all_dates.add(ds)
    
    print(f"\n汇总表包含的日期: {sorted(all_dates)}")
    
    # 统计每个日期的金额
    date_stats = {}
    for _, row in df.iterrows():
        if str(row.get('门店', '')).strip() == '合计':
            continue
        
        date_str = str(row.get('日期', ''))
        ds = ''
        if '~' in date_str:
            ds_part = date_str.split('~')[0]
            if len(ds_part) == 8:
                ds = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
        
        if ds:
            if ds not in date_stats:
                date_stats[ds] = 0.0
            date_stats[ds] += float(row.get('销售金额-小计-折后', 0) or 0)
    
    print(f"\n按日期统计:")
    for ds, total in sorted(date_stats.items()):
        print(f"  {ds}: {total:,.2f}元")
    
    # 检查数据库中这两天的数据
    print(f"\n" + "=" * 80)
    print("检查数据库中的数据")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    for ds in sorted(all_dates):
        cursor.execute("""
            SELECT COUNT(*), SUM(sales_amount)
            FROM product_sales
            WHERE data_date = %s
        """, (ds,))
        count, total = cursor.fetchone()
        print(f"\n{ds}")
        print(f"  数据库记录数: {count}条")
        print(f"  数据库总金额: {total:,.2f}元")
        
        file_total = date_stats.get(ds, 0.0)
        diff = abs(file_total - total) if total else 0.0
        
        if diff <= 1:
            print(f"  ✅ 数据正确！")
        else:
            print(f"  ❌ 金额差异: {diff:.2f}元")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
