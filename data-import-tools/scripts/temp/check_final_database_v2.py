
#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

def main():
    print("=" * 80)
    print("检查数据库最新状态（v2）")
    print("=" * 80)

    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    # 检查 order_detail
    print("\n📊 order_detail:")
    cursor.execute("SELECT data_date, COUNT(*) FROM order_detail GROUP BY data_date ORDER BY data_date DESC LIMIT 10")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 条")

    # 检查 order_daily
    print("\n📊 order_daily:")
    cursor.execute("SELECT data_date, COUNT(*) FROM order_daily GROUP BY data_date ORDER BY data_date DESC LIMIT 10")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 条")

    # 检查 product_sales_summary
    print("\n📊 product_sales_summary:")
    cursor.execute("SELECT data_date, COUNT(*) FROM product_sales_summary GROUP BY data_date ORDER BY data_date DESC")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 条")

    # 检查 product_sales_detail
    print("\n📊 product_sales_detail:")
    cursor.execute("SELECT data_date, COUNT(*) FROM product_sales_detail GROUP BY data_date ORDER BY data_date DESC")
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 条")

    # 检查 product_sales_summary 的分类信息
    print("\n🎯 product_sales_summary 分类统计:")
    cursor.execute("""
        SELECT data_date, category, COUNT(*)
        FROM product_sales_summary
        WHERE data_date = '2026-05-01'
        GROUP BY category
        ORDER BY category
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]} - {row[1]}: {row[2]} 条")

    # 检查 product_sales_detail 的包厢类型信息
    print("\n🎯 product_sales_detail 包厢类型统计:")
    cursor.execute("""
        SELECT data_date, box_type, COUNT(*)
        FROM product_sales_detail
        WHERE data_date = '2026-05-01'
        GROUP BY box_type
        ORDER BY box_type
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]} - {row[1]}: {row[2]} 条")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("检查完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

