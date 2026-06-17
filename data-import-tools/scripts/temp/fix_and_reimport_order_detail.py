
#!/usr/bin/env python3
"""
修复并重新导入 order_detail，使用原始开房时段字段
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

def clean_order_detail_table():
    """清空 order_detail 表"""
    print("清空 order_detail 表...")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE order_detail")
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ order_detail 表已清空")

def import_order_files_fixed(file_paths):
    """修复后的订单导入函数，使用原始开房时段字段"""
    print("\n导入订单明细...")
    conn = get_conn()
    cursor = conn.cursor()

    total_count = 0

    for file_path in file_paths:
        print(f"\n导入文件: {Path(file_path).name}")
        df = pd.read_csv(file_path, encoding='gbk', low_memory=False)
        print(f"  总行数: {len(df)}")

        count = 0
        for _, row in df.iterrows():
            try:
                store_name_raw = str(row.get('门店', ''))
                store_id = None
                store_name = simplify_store_name(store_name_raw)
                if store_name:
                    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
                    row_store = cursor.fetchone()
                    if row_store:
                        store_id = row_store[0]
                    else:
                        cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
                        conn.commit()
                        store_id = cursor.lastrowid

                if not store_id:
                    continue

                open_time_str = row.get('开房时间', '')
                close_time_str = row.get('关房时间', '')

                open_time = None
                close_time = None
                data_date = None

                if pd.notna(open_time_str):
                    try:
                        open_time = pd.to_datetime(open_time_str)
                        data_date = open_time.date()
                    except:
                        pass

                if pd.notna(close_time_str):
                    try:
                        close_time = pd.to_datetime(close_time_str)
                    except:
                        pass

                # 关键修复：直接使用原始文件里的开房时段字段！
                time_period = str(row.get('开房时段', ''))

                room_fee = float(row.get('房费收入', 0) or 0)
                product_fee = float(row.get('商品收入', 0) or 0)

                cursor.execute('''
                INSERT INTO order_detail
                (store_id, data_date, time_period, room_type, order_type, room_no,
                 open_time, close_time, customer_name, customer_phone, order_no,
                 should_amount, actual_amount, room_fee, product_fee, source_channel, scene)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    store_id,
                    data_date,
                    time_period,
                    str(row.get('开房类型', '')),
                    str(row.get('订单类型', '')),
                    str(row.get('包厢号', '')),
                    open_time,
                    close_time,
                    str(row.get('开房人姓名', '')),
                    str(row.get('开房人手机号', '')),
                    str(row.get('开台单号', '')),
                    float(row.get('应收金额', 0) or 0),
                    float(row.get('实收金额', 0) or 0),
                    room_fee,
                    product_fee,
                    str(row.get('来源渠道', '')),
                    str(row.get('场景', ''))
                ))
                count += 1
            except Exception as e:
                pass

        conn.commit()
        total_count += count
        print(f"  导入 {count} 条记录")

    cursor.close()
    conn.close()
    print(f"\n总计导入 {total_count} 条记录")
    return total_count

def get_order_files_from_archive():
    """直接从 archive 读取 order_export 文件"""
    archive_root = PROJECT_ROOT / 'data' / 'archive'
    
    target_dates = ['2026_04_24', '2026_04_25', '2026_04_26']
    
    print("从 archive 获取 order_export 文件...")
    files = []
    
    for date_str in target_dates:
        archive_dir = archive_root / f'source_{date_str}'
        if not archive_dir.exists():
            continue
        
        for f in sorted(archive_dir.glob('order_export_*.csv')):
            files.append(str(f))
            print(f"  找到: {f.name}")
    
    return files

def main():
    print("=" * 60)
    print("修复并重新导入订单明细")
    print("=" * 60)
    
    # 1. 清空 order_detail 表
    clean_order_detail_table()
    
    # 2. 从 archive 获取文件
    order_files = get_order_files_from_archive()
    
    if not order_files:
        print("\n❌ 未找到 order_export 文件，退出")
        return
    
    # 3. 重新导入
    import_order_files_fixed(order_files)
    
    # 4. 验证结果
    print("\n验证时段数据...")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT time_period, COUNT(*) as count
    FROM order_detail
    WHERE data_date >= '2026-04-20'
    GROUP BY time_period
    """)
    print("\n时段分布：")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
