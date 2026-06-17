#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import pymysql
import re

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, CATEGORY_MAP
from utils import simplify_store_name

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

def get_store_id(conn, store_name):
    clean = simplify_store_name(store_name)
    if not clean:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (clean,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (clean,))
    conn.commit()
    return cursor.lastrowid

def main():
    print("=" * 80)
    print("重新导入商品销售数据 - 2026-04-25")
    print("=" * 80)
    
    file_path = PROJECT_ROOT / "data" / "source" / "商品销售汇总_2026_04_26.xlsx"
    
    if not file_path.exists():
        print(f"ERROR: 文件不存在: {file_path}")
        return
    
    df = pd.read_excel(file_path)
    df.columns = [c.strip().replace('::multi-filter', '') for c in df.columns]
    print(f"\n源文件行数: {len(df)}")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    print(f"\n删除旧数据 (2026-04-25)...")
    cursor.execute("DELETE FROM product_sales WHERE data_date = '2026-04-25'")
    deleted = cursor.rowcount
    conn.commit()
    print(f"已删除 {deleted} 条记录")
    
    print(f"\n开始导入新数据...")
    count = 0
    
    for idx, row in df.iterrows():
        row_date = row.get('日期')
        if pd.isna(row_date) or row_date == '合计' or pd.isna(row.get('商品名字')) or pd.isna(row.get('门店')):
            continue
        
        store_id = get_store_id(conn, str(row.get('门店', '')))
        if not store_id:
            continue
        
        date_str = str(row_date)
        ds = ''
        if '~' in date_str:
            ds_part = date_str.split('~')[0]
            if len(ds_part) == 8:
                ds = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
        if not ds:
            continue
        
        big_category = str(row.get('系统销售类别', row.get('系统销售类别::multi-filter', '其他')))
        if big_category in ['nan', 'None', '']:
            big_category = '其他'
        big_category = CATEGORY_MAP.get(big_category, '其他')
        
        try:
            cursor.execute(
                """INSERT INTO product_sales
                (store_id, data_date, product_name, category, unit_price, quantity, sales_amount, room_type, big_category)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (store_id, ds, str(row.get('商品名字', '')), str(row.get('统计类别', '')),
                 float(row.get('单品售价', 0) or 0), int(row.get('总数量-小计', 0) or 0),
                 float(row.get('销售金额-小计-折后', 0) or 0), str(row.get('单位', '')), big_category))
            count += 1
        except Exception as e:
            print(f"  ERROR (行 {idx}): {e}")
            pass
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n导入完成!")
    print(f"  总共导入: {count} 条记录")
    print(f"  导入日期: 2026-04-25")
    
    print("\n" + "=" * 80)
    print("验证导入结果")
    print("=" * 80)
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM product_sales WHERE data_date = '2026-04-25'")
    total = cursor.fetchone()[0]
    print(f"\n数据库中 2026-04-25 的总记录数: {total}")
    print("\n按门店统计:")
    cursor.execute("""
        SELECT s.store_name, COUNT(*) as cnt, SUM(ps.sales_amount) as total_amount
        FROM product_sales ps
        JOIN stores s ON ps.store_id = s.id
        WHERE ps.data_date = '2026-04-25'
        GROUP BY s.store_name
        ORDER BY s.store_name
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条, 金额: {row[2]:.2f}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
