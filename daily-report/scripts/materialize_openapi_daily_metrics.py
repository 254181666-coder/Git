#!/usr/bin/env python3
"""
把 OpenAPI raw 明细清洗成可对账的门店日指标和商品明细。
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_daily_metrics_from_openapi_raw import (
    consume_summary,
    marketing_summary,
    parent_detail_summary,
    parent_order_shop_map,
)
from scripts.init_sqlite import main as init_sqlite
from src.config import resolve_big_category
from src.database import get_connection


def business_window(target_date: str):
    start = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=8, minute=0, second=0)
    end = start + timedelta(days=1)
    return start, end


def in_window(value, start, end):
    if not value or value == "1000-01-01 00:00:00":
        return False
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return start <= parsed < end


def store_ids(conn):
    rows = conn.execute(
        "SELECT id, fun360_shop_id, store_name FROM stores WHERE fun360_shop_id IS NOT NULL"
    ).fetchall()
    return {int(row["fun360_shop_id"]): int(row["id"]) for row in rows}


def product_catalog(conn):
    rows = conn.execute(
        "SELECT shop_id, product_name, category_id, category_name FROM raw_openapi_products"
    ).fetchall()
    catalog = {}
    for row in rows:
        catalog[(int(row["shop_id"]), row["product_name"])] = {
            "category_id": row["category_id"],
            "category": row["category_name"] or "",
        }
    return catalog


def product_items(conn, target_date: str):
    start, end = business_window(target_date)
    parent_to_shop = parent_order_shop_map(conn, target_date)
    products = defaultdict(lambda: {"quantity": 0, "sales_amount": 0.0, "rows": 0})
    catalog = product_catalog(conn)
    rows = conn.execute("SELECT parent_order_id, raw_json FROM raw_openapi_parent_order_details").fetchall()
    for row in rows:
        parent_order_id = int(row["parent_order_id"])
        shop_id = parent_to_shop.get(parent_order_id)
        if not shop_id:
            continue
        data = json.loads(row["raw_json"] or "{}")
        for order in data.get("orders", []) if isinstance(data, dict) else []:
            order_type = int(order.get("order_type") or 0)
            if order_type not in (3, 4, 5, 6, 7, 8):
                continue
            event_time = order.get("room_start_time")
            if event_time and event_time != "1000-01-01 00:00:00" and not in_window(event_time, start, end):
                continue
            for item in order.get("items", []) or []:
                quantity = int(item.get("num") or 0) - int(item.get("refund_num") or 0)
                if quantity <= 0:
                    continue
                amount = (float(item.get("item_amount") or 0) - float(item.get("refund_amount") or 0)) / 100
                product_name = item.get("item_name") or ""
                matched = catalog.get((shop_id, product_name), {})
                category_id = int(item.get("category_id") or matched.get("category_id") or 0)
                key = (shop_id, product_name, category_id)
                products[key]["quantity"] += quantity
                products[key]["sales_amount"] += amount
                products[key]["category"] = item.get("category_name") or matched.get("category", "")
                products[key]["big_category"] = resolve_big_category(
                    products[key]["category"],
                    product_name,
                )
                products[key]["rows"] += 1
    return products


def materialize(target_date: str):
    init_sqlite()
    conn = get_connection()
    try:
        shop_to_store = store_ids(conn)
        marketing = marketing_summary(conn, target_date)
        consumes = consume_summary(conn, target_date)
        details = parent_detail_summary(conn, target_date)
        shop_ids = sorted(set(marketing) | set(consumes) | set(details))

        for shop_id in shop_ids:
            store_id = shop_to_store.get(shop_id)
            if not store_id:
                continue
            m = marketing.get(shop_id, {})
            c = consumes.get(shop_id, {})
            d = details.get(shop_id, {})
            row = {
                "marketing": m,
                "consume": c,
                "detail": d,
            }
            conn.execute(
                """
                INSERT INTO openapi_daily_store_metrics (
                    store_id, shop_id, data_date, marketing_orders, marketing_amount,
                    room_orders, room_amount, product_orders, product_amount,
                    product_items, stored_orders, stored_amount, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(store_id, data_date) DO UPDATE SET
                    shop_id = excluded.shop_id,
                    marketing_orders = excluded.marketing_orders,
                    marketing_amount = excluded.marketing_amount,
                    room_orders = excluded.room_orders,
                    room_amount = excluded.room_amount,
                    product_orders = excluded.product_orders,
                    product_amount = excluded.product_amount,
                    product_items = excluded.product_items,
                    stored_orders = excluded.stored_orders,
                    stored_amount = excluded.stored_amount,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    store_id,
                    shop_id,
                    target_date,
                    m.get("marketing_orders", 0),
                    m.get("marketing_net_amount", 0) / 100,
                    d.get("detail_room_orders", c.get("member_room_orders", 0)),
                    d.get("detail_room_amount", c.get("member_room_amount", 0)),
                    d.get("detail_product_orders", c.get("member_product_orders", 0)),
                    d.get("detail_product_amount", c.get("member_product_amount", 0)),
                    d.get("detail_product_items", c.get("member_product_items", 0)),
                    c.get("member_stored_orders", 0),
                    c.get("member_stored_amount", 0),
                    json.dumps(row, ensure_ascii=False),
                ),
            )

        conn.execute("DELETE FROM openapi_product_sales_items WHERE data_date = ?", (target_date,))
        for (shop_id, product_name, category_id), value in product_items(conn, target_date).items():
            store_id = shop_to_store.get(shop_id)
            if not store_id:
                continue
            conn.execute(
                """
                INSERT INTO openapi_product_sales_items (
                    store_id, shop_id, data_date, product_name, category_id, category, big_category,
                    quantity, sales_amount, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    store_id,
                    shop_id,
                    target_date,
                    product_name,
                    category_id,
                    value.get("category", ""),
                    value.get("big_category") or resolve_big_category(value.get("category", ""), product_name),
                    value["quantity"],
                    value["sales_amount"],
                    json.dumps(value, ensure_ascii=False),
                ),
            )
        conn.commit()

        metric_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM openapi_daily_store_metrics WHERE data_date = ?",
            (target_date,),
        ).fetchone()["cnt"]
        product_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM openapi_product_sales_items WHERE data_date = ?",
            (target_date,),
        ).fetchone()["cnt"]
    finally:
        conn.close()
    print(f"已生成 OpenAPI 对账指标: 门店 {metric_count} 行，商品 {product_count} 行")


def main() -> int:
    parser = argparse.ArgumentParser(description="物化 OpenAPI 日指标")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    args = parser.parse_args()
    materialize(args.target_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
