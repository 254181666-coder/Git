
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def main():
    print("=" * 80)
    print("检查归档目录下的源文件")
    print("=" * 80)
    
    archive_dir = Path(PROJECT_ROOT) / "data" / "archive"
    
    # 检查所有 source_* 目录
    print("\n📂 归档目录下的所有源文件:")
    for d in sorted(archive_dir.glob("source_2026-05-*")):
        if d.is_dir():
            print(f"\n{d.name}:")
            for f in sorted(d.glob("*")):
                print(f"  - {f.name}")
    
    # 检查 source 目录下现有的文件
    print("\n📂 当前 source 目录:")
    source_dir = Path(PROJECT_ROOT) / "data" / "source"
    for f in sorted(source_dir.glob("*")):
        print(f"  - {f.name}")
    
    # 读取当前 source 目录下的 order_export 文件，看看实际数据日期
    order_file = source_dir / "order_export_19978_20260502095205.csv"
    if order_file.exists():
        print(f"\n📝 读取 {order_file.name} 看实际数据:")
        df = pd.read_csv(order_file, encoding="gbk", nrows=10)
        if "开房时间" in df.columns:
            df["data_date"] = pd.to_datetime(df["开房时间"]).dt.date
            print(f"   数据日期分布: {df['data_date'].value_counts().to_dict()}")
            print(f"   示例日期: {sorted(df['data_date'].unique())[:5]}")
    
    print("\n" + "=" * 80)
    print("现在的数据库状态:")
    print("=" * 80)
    
    import pymysql
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    print("\n📊 order_detail:")
    cursor.execute('''
    SELECT data_date, COUNT(*)
    FROM order_detail
    WHERE data_date >= '2026-04-28'
    GROUP BY data_date
    ORDER BY data_date DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条")
    
    print("\n📊 order_daily:")
    cursor.execute('''
    SELECT data_date, COUNT(*), SUM(revenue)
    FROM order_daily
    WHERE data_date >= '2026-04-28'
    GROUP BY data_date
    ORDER BY data_date DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条, 总营收 ¥{row[2]:.2f}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

