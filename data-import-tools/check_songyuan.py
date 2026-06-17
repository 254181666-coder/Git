
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, ARCHIVE_DIR

def main():
    print("=" * 60)
    print("检查松原一店数据")
    print("=" * 60)

    # 检查数据库中的门店
    print("\n1. 检查数据库中的门店列表:")
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT id, store_name FROM stores ORDER BY id")
    stores = cursor.fetchall()
    for s in stores:
        print(f"  {s[0]}: {s[1]}")

    # 检查store_daily表中5月11日的数据
    print("\n2. 检查store_daily表中2026-05-11的数据:")
    cursor.execute("""
        SELECT s.store_name, sd.* 
        FROM store_daily sd 
        JOIN stores s ON sd.store_id = s.id 
        WHERE sd.data_date = '2026-05-11'
        ORDER BY s.store_name
    """)
    daily_data = cursor.fetchall()
    if not daily_data:
        print("  没有找到2026-05-11的数据")
    else:
        for d in daily_data:
            print(f"  {d[0]}: 营业额 {d[4]}")

    # 检查归档文件
    print("\n3. 检查今天的归档文件:")
    today_archive = ARCHIVE_DIR / "source_2026_05_12"
    if today_archive.exists():
        daily_file = None
        for f in today_archive.iterdir():
            if "日营业数据" in f.name:
                daily_file = f
                break
        if daily_file:
            print(f"  找到日营业数据文件: {daily_file.name}")
            df = pd.read_excel(daily_file)
            print("\n4. 文件中的门店列表:")
            for idx, row in df.iterrows():
                store = row.get('门店', '')
                if pd.notna(store) and str(store).strip() != '合计':
                    print(f"  - {store}")
    else:
        print(f"  归档目录不存在: {today_archive}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
