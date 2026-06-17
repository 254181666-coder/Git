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
    print("检查商品销售汇总表")
    print("=" * 80)
    
    file_path = PROJECT_ROOT / "data" / "source" / "商品销售汇总_2026_04_26.xlsx"
    
    if not file_path.exists():
        print("文件不存在")
        return
    
    print(f"\n文件: {file_path.name}")
    df = pd.read_excel(file_path)
    print(f"总行数: {len(df)}")
    print(f"\n列: {df.columns.tolist()}")
    
    print(f"\n前5行:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(df.head())
    
    # 检查日期范围
    if '日期' in df.columns:
        unique_dates = set()
        for d in df['日期'].dropna():
            date_str = str(d)
            if '~' in date_str:
                ds_part = date_str.split('~')[0]
                if len(ds_part) == 8:
                    ds = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
                    unique_dates.add(ds)
            else:
                try:
                    dt = pd.to_datetime(d)
                    unique_dates.add(dt.strftime('%Y-%m-%d'))
                except:
                    pass
        
        print(f"\n文件中的唯一日期: {sorted(unique_dates)}")
    
    # 按门店统计
    if '门店' in df.columns:
        store_stats = {}
        for _, row in df.iterrows():
            if str(row.get('门店', '')).strip() == '合计':
                continue
            
            store = str(row.get('门店', ''))
            if store not in store_stats:
                store_stats[store] = {'count': 0, 'sales': 0.0}
            
            store_stats[store]['count'] += 1
            store_stats[store]['sales'] += float(row.get('销售金额-小计-折后', 0) or 0)
        
        print(f"\n文件中按门店统计:")
        for store, data in sorted(store_stats.items()):
            print(f"  {store:15s} {data['count']:5d}条 {data['sales']:12.2f}元")
    
    print("\n" + "=" * 80)
    print("检查数据库中的数据")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 查看数据库中4月25日的数据（因为文件是4月26日的，应该是前一天的数据）
    check_date = "2026-04-25"
    cursor.execute("""
        SELECT 
            s.store_name,
            COUNT(*) as record_count,
            SUM(ps.sales_amount) as total_sales
        FROM product_sales ps
        JOIN stores s ON ps.store_id = s.id
        WHERE ps.data_date = %s
        GROUP BY s.store_name
        ORDER BY s.store_name
    """, (check_date,))
    
    db_store_stats = {}
    print(f"\n数据库中 {check_date} 的数据:")
    for row in cursor.fetchall():
        db_store_stats[row[0]] = {'count': row[1], 'sales': row[2]}
        print(f"  {row[0]:15s} {row[1]:5d}条 {row[2]:12.2f}元")
    
    # 对比
    print(f"\n对比:")
    print(f"{'门店':15s} {'文件记录数':10s} {'数据库记录数':10s} {'文件金额':12s} {'数据库金额':12s} {'状态':10s}")
    print("-" * 80)
    
    all_stores = set(store_stats.keys()) | set(db_store_stats.keys())
    for store in sorted(all_stores):
        file_count = store_stats.get(store, {'count': 0})['count']
        db_count = db_store_stats.get(store, {'count': 0})['count']
        file_sales = store_stats.get(store, {'sales': 0})['sales']
        db_sales = db_store_stats.get(store, {'sales': 0})['sales']
        
        status = "✅" if (abs(file_count - db_count) <= 1 and abs(file_sales - db_sales) <= 1) else "❌"
        print(f"{store:15s} {file_count:10d} {db_count:10d} {file_sales:12.2f} {db_sales:12.2f} {status}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
