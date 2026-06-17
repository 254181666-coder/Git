#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pymysql
from config import MYSQL_CONFIG

VALID_STORES = {
    '鸡西店', '佳木斯店', '晨宇店', '红旗街店', '上东店',
    '通辽店', '法库店', '安达店', '榆树店', '松原一店',
    '通化店', '松原二店', '临河街店'
}

EXCLUDE_STORES = {'总部', '临河街店'}


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def cleanup_invalid_stores():
    print("=" * 60)
    print("清理无效门店数据")
    print("=" * 60)

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id, store_name FROM stores")
    all_stores = cursor.fetchall()

    print(f"\n原始门店总数: {len(all_stores)}")

    invalid_stores = []
    valid_stores = []

    for store_id, store_name in all_stores:
        if store_name in EXCLUDE_STORES:
            continue
        if store_name in VALID_STORES:
            valid_stores.append((store_id, store_name))
        else:
            invalid_stores.append((store_id, store_name))

    print(f"有效门店数: {len(valid_stores)}")
    for sid, sname in valid_stores:
        print(f"  ✓ {sname} (ID: {sid})")

    print(f"\n无效门店数(将被删除): {len(invalid_stores)}")
    for sid, sname in invalid_stores[:20]:
        print(f"  ✗ {sname} (ID: {sid})")
    if len(invalid_stores) > 20:
        print(f"  ... 还有 {len(invalid_stores) - 20} 个")

    if invalid_stores:
        print("\n开始删除无效门店...")
        invalid_ids = [sid for sid, _ in invalid_stores]
        placeholders = ','.join(['%s'] * len(invalid_ids))

        cursor.execute(f"DELETE FROM product_sales WHERE store_id IN ({placeholders})", invalid_ids)
        p_count = cursor.rowcount
        print(f"  删除 product_sales 记录: {p_count} 条")

        cursor.execute(f"DELETE FROM stored_value WHERE store_id IN ({placeholders})", invalid_ids)
        sv_count = cursor.rowcount
        print(f"  删除 stored_value 记录: {sv_count} 条")

        cursor.execute(f"DELETE FROM store_daily WHERE store_id IN ({placeholders})", invalid_ids)
        sd_count = cursor.rowcount
        print(f"  删除 store_daily 记录: {sd_count} 条")

        cursor.execute(f"DELETE FROM stores WHERE id IN ({placeholders})", invalid_ids)
        s_count = cursor.rowcount
        print(f"  删除 stores 记录: {s_count} 条")

        conn.commit()
        print("\n删除完成!")

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("清理完成")
    print("=" * 60)


if __name__ == "__main__":
    cleanup_invalid_stores()
