#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, CATEGORY_MAP

def main():
    print("=" * 80)
    print("检查4月23-26日的商品分类情况")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    print(f"\nCATEGORY_MAP配置:")
    for key, val in CATEGORY_MAP.items():
        print(f"  {key} → {val}")
    
    print(f"\n预期的big_category: {sorted(set(CATEGORY_MAP.values()))}")
    
    # 检查每个日期的big_category分布
    dates = ["2026-04-23", "2026-04-24", "2026-04-25", "2026-04-26"]
    
    for ds in dates:
        print(f"\n" + "=" * 80)
        print(f"{ds}的数据")
        print(f"=" * 80)
        
        cursor.execute("""
            SELECT 
                big_category,
                COUNT(*) as count,
                SUM(sales_amount) as total_sales
            FROM product_sales
            WHERE data_date = %s
            GROUP BY big_category
            ORDER BY total_sales DESC
        """, (ds,))
        
        print(f"\n按big_category统计:")
        print(f"  {'分类':15s} {'记录数':10s} {'金额':15s}")
        print(f"  " + "-" * 40)
        
        total_records = 0
        total_sales = 0.0
        
        for row in cursor.fetchall():
            print(f"  {row[0] or '其他':15s} {row[1]:10d} {row[2]:15,.2f}")
            total_records += row[1]
            total_sales += row[2]
        
        print(f"\n  {'合计':15s} {total_records:10d} {total_sales:15,.2f}")
        
        # 检查'其他'分类中的商品
        cursor.execute("""
            SELECT 
                product_name,
                COUNT(*) as count,
                SUM(sales_amount) as total_sales
            FROM product_sales
            WHERE data_date = %s AND (big_category = '其他' OR big_category IS NULL)
            GROUP BY product_name
            ORDER BY total_sales DESC
            LIMIT 20
        """, (ds,))
        
        other_rows = cursor.fetchall()
        
        if other_rows:
            print(f"\n'其他'分类中金额最多的20个商品:")
            print(f"  {'商品名':30s} {'记录数':10s} {'金额':15s}")
            print(f"  " + "-" * 60)
            
            for row in other_rows:
                print(f"  {str(row[0])[:28]:30s} {row[1]:10d} {row[2]:15,.2f}")
    
    # 检查分类映射是否正确
    print(f"\n" + "=" * 80)
    print("验证系统销售类别 → big_category的映射")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            big_category,
            category,
            COUNT(*) as count
        FROM product_sales
        WHERE data_date = '2026-04-25'
        GROUP BY big_category, category
        ORDER BY count DESC
        LIMIT 50
    """)
    
    print(f"\n商品分类映射 (系统销售类别 → big_category):")
    print(f"  {'big_category':15s} {'category':30s} {'记录数':10s}")
    print(f"  " + "-" * 60)
    
    for row in cursor.fetchall():
        print(f"  {row[0] or '其他':15s} {str(row[1] or '')[:28]:30s} {row[2]:10d}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
