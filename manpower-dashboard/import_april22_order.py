
#!/usr/bin/env python3
"""
导入下载文件夹里的 order_export CSV 文件到 order_detail 表
"""
import sys
import os
from pathlib import Path
import pandas as pd
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

# 门店名称映射
NAME_MAP = {
    "江南秀": "松原一店",
    "斯堡特": "松原二店",
    "红旗街": "红旗街店",
    "上东": "上东店",
    "鸡西": "鸡西店",
    "佳木斯": "佳木斯店",
    "晨宇": "晨宇店",
    "通辽": "通辽店",
    "法库": "法库店",
    "安达": "安达店",
    "榆树": "榆树店",
    "松原一": "松原一店",
    "松原二": "松原二店",
    "通化": "通化店",
    "临河街": "临河街店",
}

STORE_PREFIXES = ["私人订制KTV", "私人订制 KTV", "糖果华庭KTV", "糖果华庭 KTV"]


def simplify_store_name(store_name_raw):
    """简化门店名称"""
    if pd.isna(store_name_raw) or str(store_name_raw).strip() == "":
        return None

    name = str(store_name_raw).strip()

    # 去除前缀
    for prefix in STORE_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()

    # 应用映射
    for key, val in NAME_MAP.items():
        if key in name:
            return val

    return name


def get_store_id(conn, store_name_raw):
    """获取或创建门店ID"""
    store_name = simplify_store_name(store_name_raw)
    if not store_name:
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
    conn.commit()
    return cursor.lastrowid


def convert_time_period(raw_period, open_hour):
    """将原始时段转换为标准时段"""
    # 原始时段映射
    period_map = {
        # 日场类
        "白天": "日场",
        "买钟早场": "日场",
        "日场": "日场",
        "早场": "日场",
        "早场1": "日场",
        "早场2": "日场",
        "早次卡": "日场",
        "下午": "日场",
        "下午场": "日场",
        "白天档1": "日场",
        "日场18点": "日场",
        "日场2": "日场",
        "次卡": "日场",
        "线上次卡": "日场",
        # 黄金场类
        "黄金场": "黄金场",
        "晚场": "黄金场",
        "晚场1": "黄金场",
        "晚场2": "黄金场",
        "晚上": "黄金场",
        "买钟晚场": "黄金场",
        # 午夜场类
        "午夜场": "午夜场",
        "午夜": "午夜场",
        "午夜1": "午夜场",
        "午夜2": "午夜场",
        "午夜3": "午夜场",
        "午夜场1": "午夜场",
        "午夜场2": "午夜场",
        "午夜档": "午夜场",
        "午夜档23点": "午夜场",
        # 全天类（按时间判断）
        "全天": None,
        "全天1": None,
        "全天2": None,
        "全天3": None,
        "全天场": None,
        "全天档": None,
        "转预买": None,
    }

    raw_str = str(raw_period).strip()
    if raw_str in period_map and period_map[raw_str] is not None:
        return period_map[raw_str]

    # 按时间判断
    if 9 <= open_hour < 18:
        return "日场"
    elif 18 <= open_hour < 24:
        return "黄金场"
    else:
        return "午夜场"


def main():
    csv_path = Path("/Users/ann/Downloads/order_export_19744_20260429135505.csv")

    print("=" * 80)
    print("导入 4月22日 订单数据")
    print("=" * 80)

    if not csv_path.exists():
        print(f"❌ 文件不存在: {csv_path}")
        return

    # 读取 CSV
    df = pd.read_csv(csv_path, encoding='gbk', low_memory=False)
    print(f"\n✅ 文件读取成功！共 {len(df)} 条记录")

    # 连接数据库
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    # 收集所有涉及的日期
    all_dates = set()
    for t in df['开房时间'].dropna():
        try:
            dt = pd.to_datetime(t)
            all_dates.add(dt.date())
        except:
            pass

    # 删除旧数据
    if all_dates:
        date_strs = [str(d) for d in all_dates]
        placeholders = ','.join(['%s'] * len(date_strs))
        cursor.execute(f"DELETE FROM order_detail WHERE data_date IN ({placeholders})", date_strs)
        conn.commit()
        print(f"\n✅ 已删除旧数据: {len(date_strs)} 个日期, {cursor.rowcount} 条记录")

    # 开始导入
    count = 0
    skipped = 0

    for idx, row in df.iterrows():
        try:
            store_name_raw = str(row.get('门店', ''))
            store_id = get_store_id(conn, store_name_raw)
            if not store_id:
                skipped += 1
                continue

            open_time_str = row.get('开房时间', '')
            close_time_str = row.get('关房时间', '')

            open_time = None
            close_time = None
            data_date = None
            open_hour = 12  # 默认值

            if pd.notna(open_time_str):
                try:
                    open_time = pd.to_datetime(open_time_str)
                    data_date = open_time.date()
                    open_hour = open_time.hour
                except:
                    pass

            if pd.notna(close_time_str):
                try:
                    close_time = pd.to_datetime(close_time_str)
                except:
                    pass

            raw_period = row.get('开房时段', '')
            time_period = convert_time_period(raw_period, open_hour)

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

            if count % 100 == 0:
                print(f"⏳ 已导入 {count} 条...")

        except Exception as e:
            continue

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n✅ 导入完成！成功 {count} 条，跳过 {skipped} 条")

    # 检查导入结果
    print("\n" + "=" * 80)
    print("检查导入结果")
    print("=" * 80)
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT data_date, time_period, COUNT(*) as cnt
        FROM order_detail
        WHERE data_date >= '2026-04-20'
        GROUP BY data_date, time_period
        ORDER BY data_date DESC, time_period
    """)

    print("\n按日期时段统计:")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]} | {row[2]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ 全部完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
