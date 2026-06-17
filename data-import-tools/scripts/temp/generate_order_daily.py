#!/usr/bin/env python3
"""
重新完整重新生成order_daily表
从order_detail表中汇总数据
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
from utils import simplify_store_name
import pymysql


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def generate_order_daily():
    print("=" * 60)
    print("开始重新生成order_daily表...")
    print("=" * 60)

    conn = get_conn()
    cursor = conn.cursor()

    # 获取 stores 表的映射
    cursor.execute("SELECT id, store_name FROM stores")
    store_map = {row[0]: row[1] for row in cursor.fetchall()}

    # 先清空 order_daily 表
    print("\n1. 清空order_daily表...")
    cursor.execute("DELETE FROM order_daily")
    conn.commit()
    print("   表已清空")

    # 获取所有需要汇总的维度
    print("\n2. 从order_detail获取所有需要汇总的维度...")
    cursor.execute("""
        SELECT DISTINCT
            od.store_id,
            od.data_date,
            od.time_period,
            od.order_type,
            CASE WHEN od.source_channel LIKE '%团购%' THEN 1 ELSE 0 END as is_group_buy
        FROM order_detail od
        WHERE od.data_date IS NOT NULL
    """)

    rows = cursor.fetchall()
    total_rows = len(rows)
    print(f"   找到 {total_rows} 个维度组合")

    # 开始插入数据
    print("\n3. 开始汇总数据...")
    total_inserted = 0
    for i, row in enumerate(rows, 1):
        store_id, data_date, time_period, order_type, is_group_buy = row

        store_name = store_map.get(store_id, '')

        # 计算统计信息
        cursor.execute("""
            SELECT 
                COUNT(*) as item_count,
                SUM(actual_amount) as revenue
            FROM order_detail
            WHERE store_id = %s
                AND data_date = %s
                AND time_period = %s
                AND order_type = %s
                AND (source_channel LIKE '%%团购%%' OR %s = 0)
        """, (store_id, data_date, time_period, order_type, is_group_buy))

        item_count, revenue = cursor.fetchone()

        if item_count == 0:
            continue

        if revenue is None:
            revenue = 0

        try:
            cursor.execute("""
                INSERT INTO order_daily
                (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data_date, store_name, store_name, time_period, order_type, is_group_buy, item_count, revenue))

            total_inserted += 1

            if i % 500 == 0:
                print(f"   已处理 {i}/{total_rows} 维度，已插入 {total_inserted} 条...")
        except Exception as e:
            print(f"   插入异常: {e}")
            continue

    conn.commit()

    print(f"\n4. 汇总完成！")
    print(f"   共插入 {total_inserted} 条记录到 order_daily 表")

    # 验证结果
    print("\n5. 验证结果：")
    cursor.execute("SELECT MIN(data_date), MAX(data_date), COUNT(*) FROM order_daily")
    min_date, max_date, count_total = cursor.fetchone()
    print(f"   日期范围: {min_date} ~ {max_date}")
    print(f"   总记录数: {count_total}")

    cursor.execute("SELECT DISTINCT data_date FROM order_daily ORDER BY data_date")
    all_dates = [row[0] for row in cursor.fetchall()]
    print(f"   包含日期: {all_dates}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("order_daily表重新生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    generate_order_daily()
