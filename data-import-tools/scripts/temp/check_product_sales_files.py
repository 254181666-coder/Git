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
    print("检查商品销售文件")
    print("=" * 80)
    
    source_dir = PROJECT_ROOT / "data" / "source"
    files = sorted(source_dir.glob("商品销售明细*"))
    
    print(f"\n找到 {len(files)} 个商品销售明细文件：")
    
    for file in files:
        print(f"\n  {file.name}")
        try:
            df = pd.read_excel(file)
            print(f"    行数: {len(df)}")
            
            if '日期' in df.columns:
                unique_dates = set()
                for d in df['日期'].dropna():
                    try:
                        dt = pd.to_datetime(d).date()
                        unique_dates.add(dt)
                    except:
                        pass
                print(f"    包含日期: {sorted(unique_dates)}")
            elif '销售日期' in df.columns:
                unique_dates = set()
                for d in df['销售日期'].dropna():
                    try:
                        dt = pd.to_datetime(d).date()
                        unique_dates.add(dt)
                    except:
                        pass
                print(f"    包含日期: {sorted(unique_dates)}")
        except Exception as e:
            print(f"    读取错误: {e}")
    
    print("\n" + "=" * 80)
    print("检查数据库中的日期：")
    print("=" * 80)
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT data_date FROM product_sales ORDER BY data_date DESC
    """)
    db_dates = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    print(f"\n数据库中现有 {len(db_dates)} 个日期：")
    for d in db_dates[:20]:
        print(f"  {d}")
    
    if len(db_dates) > 20:
        print(f"  ... (还有 {len(db_dates) - 20} 个)")

if __name__ == "__main__":
    main()
