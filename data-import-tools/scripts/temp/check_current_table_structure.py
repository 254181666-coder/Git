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
    print("查看当前 product_sales 表结构")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("DESCRIBE product_sales")
    print("\n表结构:")
    for col in cursor.fetchall():
        print(f"  {col}")
    
    cursor.execute("SHOW CREATE TABLE product_sales")
    print("\n建表语句:")
    print(cursor.fetchone()[1])
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
