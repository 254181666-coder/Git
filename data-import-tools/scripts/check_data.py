#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def check_database():
    print("=" * 70)
    print(f"数据库完整性检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    conn = get_conn()
    cursor = conn.cursor()

    print("\n【1. 门店信息表 (stores)】")
    cursor.execute("SELECT COUNT(*) FROM stores")
    total = cursor.fetchone()[0]
    print(f"  总门店数: {total}")
    cursor.execute("SELECT id, store_name, created_at FROM stores ORDER BY id")
    stores = cursor.fetchall()
    for s in stores:
        print(f"    ID={s[0]}: {s[1]} (创建: {s[2]})")

    print("\n【2. 日营业数据表 (store_daily)】")
    cursor.execute("SELECT COUNT(*) FROM store_daily")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total}")

    cursor.execute("SELECT MIN(data_date), MAX(data_date) FROM store_daily")
    min_date, max_date = cursor.fetchone()
    print(f"  日期范围: {min_date} ~ {max_date}")

    cursor.execute("SELECT COUNT(DISTINCT store_id) FROM store_daily")
    stores_with_data = cursor.fetchone()[0]
    print(f"  有数据的门店数: {stores_with_data}")

    cursor.execute("""
        SELECT s.store_name, COUNT(*) as cnt, MIN(sd.data_date), MAX(sd.data_date)
        FROM store_daily sd
        JOIN stores s ON sd.store_id = s.id
        GROUP BY s.store_name
        ORDER BY s.id
    """)
    print("  各门店数据情况:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]}条 ({row[2]} ~ {row[3]})")

    print("\n【3. 储值订单表 (stored_value)】")
    cursor.execute("SELECT COUNT(*) FROM stored_value")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total}")

    cursor.execute("SELECT MIN(data_date), MAX(data_date) FROM stored_value WHERE data_date IS NOT NULL")
    result = cursor.fetchone()
    if result and result[0]:
        print(f"  日期范围: {result[0]} ~ {result[1]}")
    else:
        print("  日期范围: 无有效日期")

    cursor.execute("SELECT COUNT(DISTINCT store_id) FROM stored_value")
    stores_with_sv = cursor.fetchone()[0]
    print(f"  有数据的门店数: {stores_with_sv}")

    cursor.execute("""
        SELECT s.store_name, COUNT(*) as cnt
        FROM stored_value sv
        JOIN stores s ON sv.store_id = s.id
        GROUP BY s.store_name
        ORDER BY s.id
    """)
    print("  各门店数据情况:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]}条")

    print("\n【4. 商品销售表 (product_sales)】")
    cursor.execute("SELECT COUNT(*) FROM product_sales")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total}")

    cursor.execute("SELECT MIN(data_date), MAX(data_date) FROM product_sales")
    result = cursor.fetchone()
    if result and result[0]:
        print(f"  日期范围: {result[0]} ~ {result[1]}")
    else:
        print("  日期范围: 无数据")

    cursor.execute("SELECT COUNT(DISTINCT store_id) FROM product_sales")
    stores_with_ps = cursor.fetchone()[0]
    print(f"  有数据的门店数: {stores_with_ps}")

    cursor.execute("""
        SELECT s.store_name, COUNT(*) as cnt, MIN(ps.data_date), MAX(ps.data_date)
        FROM product_sales ps
        JOIN stores s ON ps.store_id = s.id
        GROUP BY s.store_name
        ORDER BY s.id
    """)
    print("  各门店数据情况:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]}条 ({row[2]} ~ {row[3]})")

    cursor.execute("""
        SELECT big_category, COUNT(*) as cnt
        FROM product_sales
        GROUP BY big_category
        ORDER BY cnt DESC
    """)
    print("  商品大类分布:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]}条")

    print("\n【5. 数据时效性分析】")
    today = datetime.now().date()
    for table_name, date_col in [('store_daily', 'data_date'), ('stored_value', 'data_date'), ('product_sales', 'data_date')]:
        cursor.execute(f"SELECT MAX({date_col}) FROM {table_name}")
        max_d = cursor.fetchone()[0]
        if max_d:
            if isinstance(max_d, str):
                max_d = datetime.strptime(max_d, '%Y-%m-%d').date()
            days_ago = (today - max_d).days
            print(f"  {table_name}: 最新数据 {max_d} ({days_ago}天前)")
        else:
            print(f"  {table_name}: 无数据")

    print("\n【6. 近期数据完整性检查】")
    check_dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    for ds in check_dates:
        cursor.execute("SELECT COUNT(*) FROM store_daily WHERE data_date = %s", (ds,))
        cnt = cursor.fetchone()[0]
        status = "✓" if cnt > 0 else "✗"
        print(f"  日营业 {ds}: {status} {cnt}条")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("检查完成")
    print("=" * 70)


if __name__ == "__main__":
    check_database()
