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


ROOM_ORDER_TYPES = {0, 1, 2}
PRODUCT_ORDER_TYPES = {3, 4, 5, 6, 7, 8}
GIFT_ORDER_TYPES = {7, 8}


def business_window(target_date: str):
    start = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=8, minute=0, second=0)
    end = start + timedelta(days=1)
    return start, end


def parse_time(value):
    if not value or value == "1000-01-01 00:00:00":
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def in_window(value, start, end):
    parsed = parse_time(value)
    return bool(parsed and start <= parsed < end)


def cents(value) -> float:
    try:
        return float(value or 0) / 100
    except (TypeError, ValueError):
        return 0.0


def money_text(value) -> float:
    if value in (None, ""):
        return 0.0
    text = str(value).replace("¥", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def order_event_time(order):
    direct_time = parse_time(order.get("room_start_time"))
    if direct_time:
        return direct_time.strftime("%Y-%m-%d %H:%M:%S")
    item_times = [
        parsed
        for item in order.get("items", []) or []
        for parsed in [parse_time(item.get("created_at"))]
        if parsed
    ]
    if item_times:
        return min(item_times).strftime("%Y-%m-%d %H:%M:%S")
    return None


def event_in_window(event_time, start, end):
    parsed = parse_time(event_time)
    if not parsed:
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


def clean_order_items(conn, target_date: str, shop_to_store, parent_to_shop):
    start, end = business_window(target_date)
    catalog = product_catalog(conn)
    inserted = 0
    conn.execute("DELETE FROM clean_order_item WHERE business_date = ?", (target_date,))

    rows = conn.execute("SELECT parent_order_id, raw_json FROM raw_openapi_parent_order_details").fetchall()
    for row in rows:
        parent_order_id = int(row["parent_order_id"])
        shop_id = parent_to_shop.get(parent_order_id)
        store_id = shop_to_store.get(shop_id)
        if not store_id:
            continue
        data = json.loads(row["raw_json"] or "{}")
        orders = data.get("orders", []) if isinstance(data, dict) else []
        for order in orders:
            order_type = int(order.get("order_type") or 0)
            if order_type not in PRODUCT_ORDER_TYPES:
                continue
            event_time = order_event_time(order)
            if not event_in_window(event_time, start, end):
                continue
            source_order_id = str(order.get("order_id") or "")
            sale_type = {
                3: "product",
                4: "exchange",
                5: "storage",
                6: "withdraw",
                7: "staff_gift",
                8: "stored_gift",
            }.get(order_type, "product")
            for idx, item in enumerate(order.get("items", []) or []):
                product_name = item.get("item_name") or ""
                matched = catalog.get((shop_id, product_name), {})
                category_id = int(item.get("category_id") or matched.get("category_id") or 0)
                category = item.get("category_name") or matched.get("category", "")
                quantity = float(item.get("num") or 0)
                refund_quantity = float(item.get("refund_num") or 0)
                gross_amount = cents(item.get("item_amount"))
                refund_amount = cents(item.get("refund_amount"))
                discount_amount = cents(item.get("discount_amount")) + cents(item.get("erasure_discount_amount"))
                net_amount = 0.0 if order_type in GIFT_ORDER_TYPES else gross_amount - refund_amount
                item_id = f"parent:{parent_order_id}:order:{source_order_id}:item:{item.get('ref_id') or idx}"
                payload = {
                    "parent_order_id": parent_order_id,
                    "order": order,
                    "item": item,
                    "event_time": event_time,
                }
                conn.execute(
                    """
                    INSERT INTO clean_order_item (
                        item_id, source, source_order_id, source_parent_order_id,
                        store_id, shop_id, business_date, product_name, product_code,
                        category_id, category, big_category, sale_type, is_package_item,
                        is_gift, quantity, gross_amount, discount_amount, refund_quantity,
                        refund_amount, allocated_amount, net_amount, raw_json, cleaned_at
                    )
                    VALUES (?, 'fun360', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(item_id) DO UPDATE SET
                        store_id = excluded.store_id,
                        shop_id = excluded.shop_id,
                        business_date = excluded.business_date,
                        product_name = excluded.product_name,
                        product_code = excluded.product_code,
                        category_id = excluded.category_id,
                        category = excluded.category,
                        big_category = excluded.big_category,
                        sale_type = excluded.sale_type,
                        is_package_item = excluded.is_package_item,
                        is_gift = excluded.is_gift,
                        quantity = excluded.quantity,
                        gross_amount = excluded.gross_amount,
                        discount_amount = excluded.discount_amount,
                        refund_quantity = excluded.refund_quantity,
                        refund_amount = excluded.refund_amount,
                        allocated_amount = excluded.allocated_amount,
                        net_amount = excluded.net_amount,
                        raw_json = excluded.raw_json,
                        cleaned_at = CURRENT_TIMESTAMP
                    """,
                    (
                        item_id,
                        source_order_id,
                        parent_order_id,
                        store_id,
                        shop_id,
                        target_date,
                        product_name,
                        str(item.get("ref_id") or ""),
                        category_id,
                        category,
                        resolve_big_category(category, product_name),
                        sale_type,
                        1 if item.get("parent_ref_id") else 0,
                        1 if order_type in GIFT_ORDER_TYPES else 0,
                        quantity,
                        gross_amount,
                        discount_amount,
                        refund_quantity,
                        refund_amount,
                        net_amount,
                        net_amount,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
                inserted += 1
    return inserted


def iter_consume_rows(conn):
    return conn.execute(
        """
        SELECT mobile, raw_json FROM raw_openapi_mobile_consume
        UNION ALL
        SELECT mobile, raw_json FROM raw_openapi_member_consume
        WHERE mobile NOT IN (SELECT mobile FROM raw_openapi_mobile_consume WHERE mobile IS NOT NULL)
        """
    ).fetchall()


def clean_parent_order_payment_events(conn, target_date: str, shop_to_store, parent_to_shop):
    start, end = business_window(target_date)
    inserted = 0
    rows = conn.execute("SELECT parent_order_id, raw_json FROM raw_openapi_parent_order_details").fetchall()
    for row in rows:
        parent_order_id = int(row["parent_order_id"])
        shop_id = parent_to_shop.get(parent_order_id)
        store_id = shop_to_store.get(shop_id)
        if not store_id:
            continue
        data = json.loads(row["raw_json"] or "{}")
        orders = data.get("orders", []) if isinstance(data, dict) else []
        for order in orders:
            order_type = int(order.get("order_type") or 0)
            if order_type not in ROOM_ORDER_TYPES | PRODUCT_ORDER_TYPES:
                continue
            event_time = order_event_time(order)
            if not event_in_window(event_time, start, end):
                continue
            amount = cents(order.get("paid_amount")) - cents(order.get("refund_amount"))
            if amount == 0 and order_type in GIFT_ORDER_TYPES:
                continue
            income_type = "room" if order_type in ROOM_ORDER_TYPES else "product"
            payment_event_id = f"parent:{parent_order_id}:order:{order.get('order_id')}"
            conn.execute(
                """
                INSERT INTO clean_payment_event (
                    payment_event_id, source, source_order_id, source_parent_order_id,
                    store_id, shop_id, business_date, event_time, business_source,
                    income_type, payment_method, payment_channel, amount,
                    principal_amount, gift_amount, is_actual_cashflow,
                    is_revenue_recognized, raw_json, cleaned_at
                )
                VALUES (?, 'fun360', ?, ?, ?, ?, ?, ?, 'parent_order', ?, ?, ?, ?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(payment_event_id) DO UPDATE SET
                    store_id = excluded.store_id,
                    shop_id = excluded.shop_id,
                    business_date = excluded.business_date,
                    event_time = excluded.event_time,
                    business_source = excluded.business_source,
                    income_type = excluded.income_type,
                    payment_method = excluded.payment_method,
                    payment_channel = excluded.payment_channel,
                    amount = excluded.amount,
                    principal_amount = excluded.principal_amount,
                    gift_amount = excluded.gift_amount,
                    is_actual_cashflow = excluded.is_actual_cashflow,
                    is_revenue_recognized = excluded.is_revenue_recognized,
                    raw_json = excluded.raw_json,
                    cleaned_at = CURRENT_TIMESTAMP
                """,
                (
                    payment_event_id,
                    str(order.get("order_id") or ""),
                    parent_order_id,
                    store_id,
                    shop_id,
                    target_date,
                    event_time,
                    income_type,
                    order.get("client_type") or "",
                    order.get("client_type") or "",
                    amount,
                    amount,
                    0.0,
                    0 if order_type in GIFT_ORDER_TYPES else 1,
                    json.dumps({"parent_order_id": parent_order_id, "order": order}, ensure_ascii=False),
                ),
            )
            inserted += 1
    return inserted


def clean_marketing_payment_events(conn, target_date: str, shop_to_store):
    inserted = 0
    rows = conn.execute(
        """
        SELECT order_id, shop_id, paid_amount, refund_amount, raw_json
        FROM raw_openapi_marketing_orders
        WHERE biz_day = ?
        """,
        (target_date,),
    ).fetchall()
    for row in rows:
        shop_id = int(row["shop_id"] or 0)
        store_id = shop_to_store.get(shop_id)
        if not store_id:
            continue
        raw = json.loads(row["raw_json"] or "{}")
        payments = raw.get("payments") or []
        if payments:
            payment_rows = payments
        else:
            payment_rows = [{
                "trade_id": row["order_id"],
                "paid_amount": row["paid_amount"],
                "refund_amount": row["refund_amount"],
                "pay_time": raw.get("paid_time") or raw.get("created_at"),
                "method_name": raw.get("client_name") or "",
                "method_alias": raw.get("client_type") or "",
            }]
        for payment in payment_rows:
            amount = cents(payment.get("paid_amount")) - cents(payment.get("refund_amount"))
            payment_event_id = f"marketing:{row['order_id']}:trade:{payment.get('trade_id') or 'order'}"
            event_time = payment.get("pay_time") or raw.get("paid_time") or raw.get("created_at")
            conn.execute(
                """
                INSERT INTO clean_payment_event (
                    payment_event_id, source, source_order_id, source_parent_order_id,
                    store_id, shop_id, business_date, event_time, business_source,
                    income_type, payment_method, payment_channel, amount,
                    principal_amount, gift_amount, is_actual_cashflow,
                    is_revenue_recognized, raw_json, cleaned_at
                )
                VALUES (?, 'fun360', ?, NULL, ?, ?, ?, ?, 'marketing_order',
                        'marketing', ?, ?, ?, ?, 0, 1, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(payment_event_id) DO UPDATE SET
                    store_id = excluded.store_id,
                    shop_id = excluded.shop_id,
                    business_date = excluded.business_date,
                    event_time = excluded.event_time,
                    payment_method = excluded.payment_method,
                    payment_channel = excluded.payment_channel,
                    amount = excluded.amount,
                    principal_amount = excluded.principal_amount,
                    raw_json = excluded.raw_json,
                    cleaned_at = CURRENT_TIMESTAMP
                """,
                (
                    payment_event_id,
                    str(row["order_id"]),
                    store_id,
                    shop_id,
                    target_date,
                    event_time,
                    payment.get("method_name") or "",
                    payment.get("method_alias") or "",
                    amount,
                    amount,
                    json.dumps({"order": raw, "payment": payment}, ensure_ascii=False),
                ),
            )
            inserted += 1
    return inserted


def clean_stored_payment_events(conn, target_date: str, shop_to_store):
    start, end = business_window(target_date)
    inserted = 0
    seen = set()
    for row in iter_consume_rows(conn):
        data = json.loads(row["raw_json"] or "{}")
        consume = data.get("consume_info", data)
        for item in consume.get("stored_info", []) or []:
            event_time = item.get("pay_time") or item.get("created_at")
            if not in_window(event_time, start, end):
                continue
            shop_id = int(item.get("shop_id") or 0)
            store_id = shop_to_store.get(shop_id)
            if not store_id:
                continue
            stored_order_id = item.get("stored_order_id") or item.get("order_id")
            payment_event_id = f"stored:{stored_order_id or row['mobile'] + ':' + event_time}"
            if payment_event_id in seen:
                continue
            seen.add(payment_event_id)
            amount = money_text(item.get("stored_amount_text"))
            trade_ids = item.get("trade_ids") or {}
            conn.execute(
                """
                INSERT INTO clean_payment_event (
                    payment_event_id, source, source_order_id, source_parent_order_id,
                    store_id, shop_id, business_date, event_time, business_source,
                    income_type, payment_method, payment_channel, amount,
                    principal_amount, gift_amount, is_actual_cashflow,
                    is_revenue_recognized, raw_json, cleaned_at
                )
                VALUES (?, 'fun360', ?, NULL, ?, ?, ?, ?, 'member_recharge',
                        'stored', ?, ?, ?, ?, 0, 1, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(payment_event_id) DO UPDATE SET
                    store_id = excluded.store_id,
                    shop_id = excluded.shop_id,
                    business_date = excluded.business_date,
                    event_time = excluded.event_time,
                    payment_method = excluded.payment_method,
                    payment_channel = excluded.payment_channel,
                    amount = excluded.amount,
                    principal_amount = excluded.principal_amount,
                    raw_json = excluded.raw_json,
                    cleaned_at = CURRENT_TIMESTAMP
                """,
                (
                    payment_event_id,
                    str(stored_order_id or ""),
                    store_id,
                    shop_id,
                    target_date,
                    event_time,
                    item.get("client_name") or "",
                    ",".join(str(key) for key in trade_ids.keys()),
                    amount,
                    amount,
                    json.dumps({"mobile": row["mobile"], "stored": item}, ensure_ascii=False),
                ),
            )
            inserted += 1
    return inserted


def clean_payment_events(conn, target_date: str, shop_to_store, parent_to_shop):
    conn.execute("DELETE FROM clean_payment_event WHERE business_date = ?", (target_date,))
    parent_count = clean_parent_order_payment_events(conn, target_date, shop_to_store, parent_to_shop)
    marketing_count = clean_marketing_payment_events(conn, target_date, shop_to_store)
    stored_count = clean_stored_payment_events(conn, target_date, shop_to_store)
    return parent_count + marketing_count + stored_count


def materialize_daily_store_revenue(conn, target_date: str):
    conn.execute("DELETE FROM mart_daily_store_revenue WHERE business_date = ?", (target_date,))
    rows = conn.execute(
        """
        SELECT
            store_id,
            shop_id,
            SUM(CASE WHEN is_revenue_recognized = 1 THEN amount ELSE 0 END) AS recognized_revenue,
            SUM(CASE WHEN is_actual_cashflow = 1 THEN amount ELSE 0 END) AS actual_cashflow,
            SUM(CASE WHEN income_type = 'room' THEN amount ELSE 0 END) AS room_amount,
            SUM(CASE WHEN income_type = 'product' THEN amount ELSE 0 END) AS product_amount,
            SUM(CASE WHEN income_type = 'stored' THEN amount ELSE 0 END) AS stored_amount,
            SUM(CASE WHEN income_type = 'marketing' THEN amount ELSE 0 END) AS marketing_amount,
            SUM(CASE WHEN income_type NOT IN ('room', 'product', 'stored', 'marketing') THEN amount ELSE 0 END) AS other_amount,
            COUNT(DISTINCT CASE WHEN income_type = 'room' THEN source_parent_order_id END) AS room_sessions
        FROM clean_payment_event
        WHERE business_date = ?
        GROUP BY store_id, shop_id
        """,
        (target_date,),
    ).fetchall()
    for row in rows:
        recognized = float(row["recognized_revenue"] or 0)
        raw_payload = {
            "source": "clean_payment_event",
            "note": "stored income is recognized on the recharge business day",
        }
        conn.execute(
            """
            INSERT INTO mart_daily_store_revenue (
                store_id, shop_id, business_date, total_revenue, net_revenue,
                recognized_revenue, actual_cashflow, room_amount, product_amount,
                stored_amount, marketing_amount, other_amount, room_sessions,
                raw_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                row["store_id"],
                row["shop_id"],
                target_date,
                recognized,
                recognized,
                recognized,
                float(row["actual_cashflow"] or 0),
                float(row["room_amount"] or 0),
                float(row["product_amount"] or 0),
                float(row["stored_amount"] or 0),
                float(row["marketing_amount"] or 0),
                float(row["other_amount"] or 0),
                int(row["room_sessions"] or 0),
                json.dumps(raw_payload, ensure_ascii=False),
            ),
        )
    return len(rows)


def materialize(target_date: str):
    init_sqlite()
    conn = get_connection()
    try:
        shop_to_store = store_ids(conn)
        parent_to_shop = parent_order_shop_map(conn, target_date)
        clean_item_count = clean_order_items(conn, target_date, shop_to_store, parent_to_shop)
        clean_payment_count = clean_payment_events(conn, target_date, shop_to_store, parent_to_shop)
        mart_revenue_count = materialize_daily_store_revenue(conn, target_date)

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
    print(
        "已生成 OpenAPI 清洗与 mart: "
        f"clean_order_item {clean_item_count} 行，"
        f"clean_payment_event {clean_payment_count} 行，"
        f"mart_daily_store_revenue {mart_revenue_count} 行；"
        f"兼容对账表门店 {metric_count} 行，商品 {product_count} 行"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="物化 OpenAPI 日指标")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    args = parser.parse_args()
    materialize(args.target_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
