#!/usr/bin/env python3
"""
每日数据导入脚本 - 定时任务版本
1. 从 data/source 读取数据
2. 导入到数据库
3. 导入成功后备份文件到 archive
"""
import sys
from pathlib import Path
from datetime import datetime
import shutil
import glob as glob_module

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.import_data import main as import_main_data
from scripts.import_order_detail import main as import_order_detail
from scripts.import_member_balance import main as import_member_balance
from scripts.import_stored_commission import main as import_stored_commission
from scripts.import_product_commission import main as import_product_commission
from scripts.import_card_detail import main as import_card_detail
from config import MYSQL_CONFIG, SOURCE_DIR, ARCHIVE_DIR, LOGS_DIR
from utils import simplify_store_name
import pymysql


def get_today_str():
    return datetime.now().strftime('%Y%m%d')


def generate_order_daily():
    """从 order_detail 表生成 order_daily 表"""
    print("\n【7/7】更新 order_daily 汇总表...")
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 获取 stores 表的映射
    cursor.execute("SELECT id, store_name FROM stores")
    store_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 先清空 order_daily 表，然后重新生成
    cursor.execute("DELETE FROM order_daily")
    conn.commit()
    
    # 获取所有需要汇总的维度
    cursor.execute('''
    SELECT DISTINCT
        od.store_id,
        od.data_date,
        od.time_period,
        od.order_type,
        CASE WHEN od.source_channel LIKE '%团购%' THEN 1 ELSE 0 END as is_group_buy
    FROM order_detail od
    WHERE od.data_date IS NOT NULL
    ''')
    
    rows = cursor.fetchall()
    total_inserted = 0
    
    for row in rows:
        store_id, data_date, time_period, order_type, is_group_buy = row
        
        store_name = store_map.get(store_id, '')
        
        # 计算统计信息
        cursor.execute('''
        SELECT 
            COUNT(*) as item_count,
            SUM(actual_amount) as revenue
        FROM order_detail
        WHERE store_id = %s
            AND data_date = %s
            AND time_period = %s
            AND order_type = %s
            AND (source_channel LIKE '%%团购%%' OR %s = 0)
        ''', (store_id, data_date, time_period, order_type, is_group_buy))
        
        item_count, revenue = cursor.fetchone()
        
        if item_count == 0:
            continue
        
        try:
            cursor.execute('''
            INSERT INTO order_daily
            (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (data_date, store_name, store_name, time_period, order_type, is_group_buy, item_count, revenue))
            
            total_inserted += 1
        except Exception as e:
            pass
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"   order_daily 表更新完成，共 {total_inserted} 条记录")


def archive_source_files():
    """归档 source 目录中的文件到 backup/source_history"""
    archive_dir = ARCHIVE_DIR / 'source_history'

    if not archive_dir.exists():
        archive_dir.mkdir(parents=True)

    source_files = list(SOURCE_DIR.glob('*'))
    archived_count = 0

    for f in source_files:
        if f.name.startswith('.'):
            continue
        if f.name == '25nian.xlsx':
            continue
        try:
            dest = archive_dir / f.name
            shutil.move(str(f), str(dest))
            archived_count += 1
            print(f'  已归档: {f.name}')
        except Exception as e:
            print(f'  归档失败: {f.name} - {e}')

    return archived_count


def main():
    print("=" * 60)
    print(f"每日数据导入 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n【1/7】导入日营业、储值、商品销售数据...")
    import_main_data()

    print("\n【2/7】导入订单消费明细...")
    import_order_detail()

    print("\n【3/7】导入会员余额变动...")
    import_member_balance()

    print("\n【4/7】导入储值提成数据...")
    import_stored_commission()

    print("\n【5/7】导入商品提成数据...")
    import_product_commission()

    print("\n【6/7】导入卡券明细数据...")
    import_card_detail()
    
    # 新增：更新 order_daily 表
    generate_order_daily()

    print("\n" + "=" * 60)
    print("数据导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
