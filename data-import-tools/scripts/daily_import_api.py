#!/usr/bin/env python3
"""
每日数据导入 - API版本
从业务系统OpenAPI拉取数据，导入数据库
替换原来的影刀下载Excel方式
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import pymysql

from api_client import BusinessAPIClient
from utils import send_feishu_notification, simplify_store_name
from config import LOGS_DIR, MYSQL_CONFIG, PRODUCT_CATEGORY_MAP

LOGS_DIR.mkdir(exist_ok=True)


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOGS_DIR / f"import_api_{datetime.now().strftime('%Y%m%d')}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)


def get_product_category(product_name):
    """根据商品名称获取分类"""
    if not product_name:
        return '其他'
    for key, category in PRODUCT_CATEGORY_MAP.items():
        if key in str(product_name):
            return category
    return '其他'


def sync_shops(conn, shops):
    """同步门店列表到数据库"""
    cursor = conn.cursor()
    inserted = 0
    updated = 0
    
    for shop in shops:
        shop_id = shop['shop_id']
        name = shop['name']
        clean_name = simplify_store_name(name)
        
        if not clean_name:
            log(f"  跳过门店 {name}（排除）")
            continue
        
        # 检查是否存在
        cursor.execute("SELECT id FROM stores WHERE store_name = %s", (clean_name,))
        row = cursor.fetchone()
        
        if row is None:
            # 插入新门店
            cursor.execute("""
                INSERT INTO stores (store_name, shop_id, address, province_code, city_code, district_code)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                clean_name,
                shop_id,
                shop.get('address'),
                shop.get('province'),
                shop.get('city'),
                shop.get('district'),
            ))
            inserted += 1
        else:
            # 更新门店信息
            cursor.execute("""
                UPDATE stores SET shop_id = %s, address = %s WHERE id = %s
            """, (shop_id, shop.get('address'), row[0]))
            updated += 1
    
    conn.commit()
    log(f"  门店同步完成: 新增 {inserted}, 更新 {updated}")
    return inserted + updated


def sync_employees(conn, users):
    """同步员工列表到数据库"""
    cursor = conn.cursor()
    inserted = 0
    updated = 0
    
    for user in users:
        uid = user['uid']
        username = user['username']
        nickname = user.get('nickname', username)
        
        # 检查是否存在
        cursor.execute("SELECT id FROM employees WHERE uid = %s", (uid,))
        row = cursor.fetchone()
        
        if row is None:
            cursor.execute("""
                INSERT INTO employees (uid, username, nickname, is_super, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                uid,
                username,
                nickname,
                user.get('is_super', 0),
                user.get('status', 1),
            ))
            inserted += 1
        else:
            cursor.execute("""
                UPDATE employees SET username = %s, nickname = %s, is_super = %s, status = %s
                WHERE id = %s
            """, (
                username,
                nickname,
                user.get('is_super', 0),
                user.get('status', 1),
                row[0]
            ))
            updated += 1
    
    conn.commit()
    log(f"  员工同步完成: 新增 {inserted}, 更新 {updated}")
    return inserted + updated


def insert_orders(conn, orders):
    """插入订单数据到数据库"""
    cursor = conn.cursor()
    inserted = 0
    
    for order in orders:
        # 插入订单主表
        cursor.execute("""
            INSERT IGNORE INTO orders (
                order_id, renew, order_type, total_amount_orig, discount_amount,
                member_id, creator_id, seller_id, discount_type_bit, paid_amount,
                erasure_discount_amount, refund_amount, refund_item_amount,
                room_start_time, room_end_time, client_type, creator_name, seller_name, member_mp_open_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order['order_id'],
            order.get('renew', 0),
            order.get('order_type', 0),
            order.get('total_amount_orig', 0),
            order.get('discount_amount', 0),
            order.get('member_id', 0),
            order.get('creator_id', 0),
            order.get('seller_id', 0),
            order.get('discount_type_bit', 0),
            order.get('paid_amount', 0),
            order.get('erasure_discount_amount', 0),
            order.get('refund_amount', 0),
            order.get('refund_item_amount', 0),
            order.get('room_start_time'),
            order.get('room_end_time'),
            order.get('client_type'),
            order.get('creator_name'),
            order.get('seller_name'),
            order.get('member_mp_open_id'),
        ))
        
        order_id = order['order_id']
        items = order.get('items', [])
        
        # 插入订单明细
        for item in items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, ref_id, parent_ref_id, item_name, item_type,
                    item_amount, item_price, category_id, num, refund_num, refund_amount,
                    discount_amount, discount_type_bit, vending_machine_produce, vending_machine_produce_num,
                    erasure_discount_amount, taste, created_at, location
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_id,
                item.get('ref_id'),
                item.get('parent_ref_id', 0),
                item.get('item_name'),
                item.get('item_type', 0),
                item.get('item_amount', 0),
                item.get('item_price', 0),
                item.get('category_id', 0),
                item.get('num', 1),
                item.get('refund_num', 0),
                item.get('refund_amount', 0),
                item.get('discount_amount', 0),
                item.get('discount_type_bit', 0),
                item.get('vending_machine_produce', 0),
                item.get('vending_machine_produce_num', 0),
                item.get('erasure_discount_amount', 0),
                item.get('taste'),
                item.get('created_at'),
                item.get('location'),
            ))
            inserted += 1
    
    conn.commit()
    log(f"  订单插入完成: {inserted} 条明细")
    return inserted


def main(target_date=None):
    print("=" * 60)
    print(f"每日数据导入(API版本) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = datetime.now()
    success = True
    error_msg = ""
    
    # 默认获取昨天的数据
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    
    date_str = target_date.strftime('%Y-%m-%d')
    start_date_str = f"{date_str} 00:00:00"
    end_date_str = f"{date_str} 23:59:59"
    
    log(f"目标日期: {date_str}")
    
    try:
        api_client = BusinessAPIClient()
        conn = get_conn()
        
        # 1. 同步门店列表
        print("\n【1/5】同步门店列表...")
        shops = api_client.get_shop_list()
        if shops is None:
            raise Exception("获取门店列表失败")
        sync_shops(conn, shops)
        
        # 2. 同步员工列表
        print("\n【2/5】同步员工列表...")
        users = api_client.get_user_list()
        if users is None:
            raise Exception("获取员工列表失败")
        sync_employees(conn, users)
        
        # 3. 获取订单数据（按日期）
        print("\n【3/5】获取订单数据...")
        page = 1
        page_size = 100
        total_orders = 0
        total_items = 0
        
        while True:
            orders = api_client.get_orders_by_date(start_date_str, end_date_str, page, page_size)
            if not orders:
                break
            
            cnt = insert_orders(conn, orders)
            total_orders += len(orders)
            total_items += cnt
            
            # 如果不够一页，说明没有更多了
            if len(orders) < page_size:
                break
            
            page += 1
        
        log(f"  订单导入完成: {total_orders} 个订单，{total_items} 条明细")
        
        # 4. TODO: 获取储值数据
        print("\n【4/5】获取储值数据... [待添加具体接口]")
        # 储值数据同步待接口确认
        
        # 5. TODO: 获取会员余额变动
        print("\n【5/5】获取会员余额变动... [待添加具体接口]")
        # 余额变动同步待接口确认
        
        conn.close()
        
    except Exception as e:
        success = False
        error_msg = str(e)
        log(f"\n错误: {error_msg}")
    
    # 结束计时
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 发送通知
    if success:
        msg = (
            f"✅ 数据导入成功\n"
            f"日期: {date_str}\n"
            f"耗时: {duration:.1f}秒"
        )
        send_feishu_notification("数据导入完成", msg)
    else:
        msg = (
            f"❌ 数据导入失败\n"
            f"日期: {date_str}\n"
            f"错误: {error_msg}"
        )
        send_feishu_notification("数据导入失败，请检查", msg)
    
    print("\n" + "=" * 60)
    if success:
        print("导入完成！")
    else:
        print("导入失败！")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 支持命令行指定日期
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        main(target_date)
    else:
        main()
