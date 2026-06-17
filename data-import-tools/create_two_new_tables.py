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
    print("创建两个新表")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 1. 创建 product_sales_summary 表（商品销售汇总表）
    print("\n创建 product_sales_summary 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_sales_summary (
            id int NOT NULL AUTO_INCREMENT,
            store_id int NOT NULL,
            data_date date NOT NULL,
            product_name text COLLATE utf8mb4_unicode_ci,
            product_code text COLLATE utf8mb4_unicode_ci,
            category text COLLATE utf8mb4_unicode_ci,
            system_category text COLLATE utf8mb4_unicode_ci,
            unit text COLLATE utf8mb4_unicode_ci,
            unit_price double DEFAULT '0',
            quantity int DEFAULT '0',
            sales_amount double DEFAULT '0',
            big_category text COLLATE utf8mb4_unicode_ci,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    print("✅ product_sales_summary 表创建成功！")
    
    # 2. 创建 product_sales_detail 表（商品销售明细表）
    print("\n创建 product_sales_detail 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_sales_detail (
            id int NOT NULL AUTO_INCREMENT,
            store_id int NOT NULL,
            data_date date NOT NULL,
            product_name text COLLATE utf8mb4_unicode_ci,
            product_code text COLLATE utf8mb4_unicode_ci,
            package text COLLATE utf8mb4_unicode_ci,
            room_no text COLLATE utf8mb4_unicode_ci,
            room_type text COLLATE utf8mb4_unicode_ci,
            quantity int DEFAULT '0',
            sales_amount double DEFAULT '0',
            order_type text COLLATE utf8mb4_unicode_ci,
            created_at datetime DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    print("✅ product_sales_detail 表创建成功！")
    
    print("\n两个新表都创建成功！")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
