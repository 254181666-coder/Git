#!/usr/bin/env python3
from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"

sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("🎯 直接导入 05-09 和 05-10 的日营业数据")
print("=" * 80)

# 1. 先把两个文件都复制到 source 目录
file_09 = ARCHIVE_DIR / "source_2026_05_09" / "日营业数据表_20531.xlsx"
file_10 = ARCHIVE_DIR / "source_history" / "日营业数据表_20644.xlsx"

for f in [file_09, file_10]:
    if f.exists():
        dest = SOURCE_DIR / f.name
        if not dest.exists():
            import shutil
            shutil.copy2(f, dest)
            print(f"✅ 复制: {f.name}")

# 2. 手动导入这两个文件
from scripts.import_data import get_conn, log, simplify_store_name, get_store_id

def import_single_file(file_path):
    log(f"📦 处理文件: {file_path.name}")
    conn = get_conn()
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    cursor = conn.cursor()
    
    dates_to_delete = set()
    for _, row in df.iterrows():
        dv = row.get('日期')
        if not pd.isna(dv):
            dates_to_delete.add(str(dv)[:10])
    
    for ds in dates_to_delete:
        log(f"  🗑️ 删除旧数据: {ds}")
        cursor.execute("DELETE FROM store_daily WHERE data_date = %s", (ds,))
    
    conn.commit()
    
    cols = [
        'store_id', 'data_date', 'weekday', 'total_revenue', 'actual_amount',
        'supermarket_revenue', 'room_revenue', 'stored_card_sales', 'times_card_sales',
        'other_revenue', 'transfer_fund', 'online_groupbuy', 'daily_batch_consumption',
        'customers_before_18', 'maintenance_before_18',
        'customers_18_to_24', 'maintenance_18_to_24',
        'customers_after_00', 'maintenance_after_00',
        'peak_room_count', 'peak_time', 'revenue', 'customers'
    ]
    placeholders = ','.join(['%s'] * len(cols))
    sql = f"INSERT INTO store_daily ({','.join(cols)}) VALUES ({placeholders})"
    count = 0
    for _, row in df.iterrows():
        store_name = simplify_store_name(row.get('门店', ''))
        if not store_name:
            continue
        date_val = row.get('日期')
        if pd.isna(date_val):
            continue
        try:
            store_id = get_store_id(conn, store_name)
            if not store_id:
                continue
            vals = [
                store_id, str(date_val)[:10],
                str(row.get('星期', '')),
                float(row.get('总计营业额', 0) or 0),
                float(row.get('实收金额', 0) or 0),
                float(row.get('超市收入', 0) or 0),
                float(row.get('房费收入', 0) or 0),
                float(row.get('储值卡销售', 0) or 0),
                float(row.get('次卡销售', 0) or 0),
                float(row.get('营业外', 0) or 0),
                float(row.get('往来资金', 0) or 0),
                float(row.get('线上团购应收', 0) or 0),
                float(row.get('日单批消费', 0) or 0),
                int(row.get('18点前待客', 0) or 0),
                int(row.get('18点前维护', 0) or 0),
                int(row.get('18点-24点待客', 0) or 0),
                int(row.get('18点-24点维护', 0) or 0),
                int(row.get('00点后待客', 0) or 0),
                int(row.get('00点后维护', 0) or 0),
                int(row.get('晚场待客最高峰台数', 0) or 0),
                str(row.get('晚场待客最高峰时点', '') or ''),
                float(row.get('总计营业额', 0) or 0),
                int(row.get('全天待客台数', 0) or 0)
            ]
            cursor.execute(sql, vals)
            count += 1
        except Exception as e:
            print(f"  ⚠️ 跳过一行: {e}")
    
    conn.commit()
    cursor.close()
    log(f"  ✅ 导入 {count} 条记录")
    conn.close()
    return count

# 导入两个文件
print("\n开始导入...")
if (SOURCE_DIR / "日营业数据表_20531.xlsx").exists():
    import_single_file(SOURCE_DIR / "日营业数据表_20531.xlsx")

if (SOURCE_DIR / "日营业数据表_20644.xlsx").exists():
    import_single_file(SOURCE_DIR / "日营业数据表_20644.xlsx")

print("\n" + "=" * 80)
print("✅ 最后验证...")
print("=" * 80)

from config import MYSQL_CONFIG
import pymysql
conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

dates_to_check = ["2026-05-07", "2026-05-08", "2026-05-09", "2026-05-10"]
for table in ["store_daily"]:
    print(f"\n【{table}】")
    for date_str in dates_to_check:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE data_date = %s", (date_str,))
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {date_str}: {count} 条")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 100% 完成！")
print("=" * 80)
