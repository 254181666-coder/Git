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
    print("检查商品销售明细文件内容")
    print("=" * 80)
    
    source_dir = PROJECT_ROOT / "data" / "source"
    files = sorted(source_dir.glob("商品销售明细*"))
    
    for file in files:
        print(f"\n\n{file.name}:")
        df = pd.read_excel(file)
        print(f"  行数: {len(df)}")
        print(f"  列: {df.columns.tolist()}")
        
        if len(df) > 0:
            print(f"\n  前3行预览:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 200)
            print(df.head(3))
            
            print(f"\n  唯一日期:")
            unique_dates = set()
            if '销售日期' in df.columns:
                col = '销售日期'
            elif '日期' in df.columns:
                col = '日期'
            else:
                col = None
            
            if col:
                for d in df[col].dropna():
                    try:
                        dt = pd.to_datetime(d)
                        unique_dates.add(dt.date())
                    except:
                        pass
            
            if unique_dates:
                print(f"    {sorted(unique_dates)}")
            else:
                print(f"    没有找到日期")
            
            print(f"\n  按日期统计:")
            if col:
                df['data_date'] = pd.to_datetime(df[col]).dt.date
                date_counts = df.groupby('data_date').size()
                print(date_counts)
            
            print(f"\n  按门店统计:")
            if '门店名称' in df.columns:
                store_counts = df.groupby('门店名称').size()
                print(store_counts)
            elif '门店' in df.columns:
                store_counts = df.groupby('门店').size()
                print(store_counts)

if __name__ == "__main__":
    main()
