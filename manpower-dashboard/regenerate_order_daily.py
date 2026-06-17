
#!/usr/bin/env python3
"""
从 order_detail 表重新生成 order_daily 表
"""
import sys
import os
import pymysql
from datetime import datetime

# MySQL 配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "CHANGE_ME_MYSQL_PASSWORD",
    "database": "ktv_analysis",
    "charset": "utf8mb4"
}


def main():
    print("=" * 80)
    print("重新生成 order_daily 表")
    print("=" * 80)

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    # 先查询数据库中有哪些日期
    cursor.execute("""
        SELECT DISTINCT data_date
        FROM order_detail
        ORDER BY data_date DESC
    """)
    all_dates = [row[0] for row in cursor.fetchall()]
    print(f"\n✅ 找到 {len(all_dates)} 个日期")
    for d in all_dates[:10]:
        print(f"  - {d}")
    if len(all_dates) > 10:
        print(f"  ... 还有 {len(all_dates)-10} 个")

    # 删除旧数据
    if all_dates:
        date_strs = [str(d) for d in all_dates]
        placeholders = ','.join(['%s'] * len(date_strs))
        cursor.execute(f"DELETE FROM order_daily WHERE data_date IN ({placeholders})", date_strs)
        conn.commit()
        print(f"\n✅ 已删除旧 order_daily 数据: {cursor.rowcount} 条")

    # 从 order_detail 汇总数据到 order_daily
    print("\n⏳ 正在汇总数据...")
    sql = """
        INSERT INTO order_daily
        (data_date, store_name, store_name_raw, time_period, order_type, is_group_buy, item_count, revenue)
        SELECT
            od.data_date,
            s.store_name,
            s.store_name as store_name_raw,
            od.time_period,
            od.order_type,
            CASE
                WHEN od.source_channel LIKE '%%团购%%' THEN '团购'
                ELSE '非团购'
            END as is_group_buy,
            COUNT(*) as item_count,
            SUM(od.actual_amount) as revenue
        FROM order_detail od
        JOIN stores s ON od.store_id = s.id
        WHERE od.data_date BETWEEN %s AND %s
          AND od.time_period IN ('日场', '黄金场', '午夜场')
        GROUP BY od.data_date, s.store_name, od.time_period, od.order_type, is_group_buy
        ORDER BY od.data_date, s.store_name, od.time_period, od.order_type
    """
    cursor.execute(sql, (all_dates[-1], all_dates[0]))

    conn.commit()
    print(f"\n✅ 成功插入 {cursor.rowcount} 条记录到 order_daily 表")

    # 验证结果
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)
    cursor.execute("""
        SELECT data_date, time_period, COUNT(*) as cnt, SUM(item_count) as total_items, SUM(revenue) as total_rev
        FROM order_daily
        WHERE data_date >= '2026-04-20'
        GROUP BY data_date, time_period
        ORDER BY data_date DESC, time_period
    """)

    print("\n按日期时段统计（order_daily）:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]} | 记录数={row[2]} | 商品数={row[3]} | 营收={row[4]}")

    # 检查是否包含 4月22日完整数据
    print("\n" + "=" * 80)
    print("检查 4月22日")
    print("=" * 80)
    cursor.execute("""
        SELECT time_period, COUNT(*) as cnt, SUM(item_count) as items, SUM(revenue) as rev
        FROM order_daily
        WHERE data_date = '2026-04-22'
        GROUP BY time_period
        ORDER BY time_period
    """)
    print("\n4月22日时段分布:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ 全部完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
