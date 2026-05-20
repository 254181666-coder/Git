#!/usr/bin/env python3
"""
从 OpenAPI raw 表构建每日验证指标。

这是清洗汇总的第一版，用于对账，不直接替代正式日报表。
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection


def business_window(target_date: str):
    start = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=8, minute=0, second=0)
    end = start + timedelta(days=1)
    return start, end


def parse_time(value: Any) -> Optional[datetime]:
    if not value or value == "1000-01-01 00:00:00":
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_amount_text(value: Any) -> float:
    if value in (None, ""):
        return 0
    text = str(value).replace("¥", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0


def in_window(value: Any, start: datetime, end: datetime) -> bool:
    parsed = parse_time(value)
    return bool(parsed and start <= parsed < end)


def load_store_names(conn) -> Dict[int, str]:
    rows = conn.execute(
        "SELECT fun360_shop_id, store_name FROM stores WHERE fun360_shop_id IS NOT NULL"
    ).fetchall()
    return {int(row["fun360_shop_id"]): row["store_name"] for row in rows}


def marketing_summary(conn, target_date: str):
    rows = conn.execute(
        """
        SELECT shop_id, COUNT(*) AS order_count,
               SUM(paid_amount - refund_amount) AS net_amount
        FROM raw_openapi_marketing_orders
        WHERE biz_day = ?
        GROUP BY shop_id
        """,
        (target_date,),
    ).fetchall()
    return {
        int(row["shop_id"]): {
            "marketing_orders": int(row["order_count"] or 0),
            "marketing_net_amount": float(row["net_amount"] or 0),
        }
        for row in rows
    }


def consume_summary(conn, target_date: str):
    start, end = business_window(target_date)
    summary = defaultdict(lambda: {
        "member_room_orders": 0,
        "member_room_amount": 0.0,
        "member_product_orders": 0,
        "member_product_amount": 0.0,
        "member_product_items": 0,
        "member_stored_orders": 0,
        "member_stored_amount": 0.0,
    })
    rows = conn.execute(
        """
        SELECT mobile, raw_json FROM raw_openapi_mobile_consume
        UNION ALL
        SELECT mobile, raw_json FROM raw_openapi_member_consume
        WHERE mobile NOT IN (SELECT mobile FROM raw_openapi_mobile_consume WHERE mobile IS NOT NULL)
        """
    ).fetchall()
    for row in rows:
        data = json.loads(row["raw_json"] or "{}")
        consume = data.get("consume_info", data)

        for item in consume.get("parent_order_info", []) or []:
            if not in_window(item.get("pay_time") or item.get("created_at"), start, end):
                continue
            shop_id = int(item.get("shop_id") or 0)
            if not shop_id:
                continue
            summary[shop_id]["member_room_orders"] += 1
            summary[shop_id]["member_room_amount"] += parse_amount_text(item.get("open_amount_text"))

        for item in consume.get("order_info", []) or []:
            if not in_window(item.get("pay_time") or item.get("created_at"), start, end):
                continue
            shop_id = int(item.get("shop_id") or 0)
            if not shop_id:
                continue
            summary[shop_id]["member_product_orders"] += 1
            summary[shop_id]["member_product_amount"] += parse_amount_text(item.get("open_amount_text"))
            products = item.get("product_list") or []
            summary[shop_id]["member_product_items"] += sum(int(p.get("num") or 0) for p in products)

        for item in consume.get("stored_info", []) or []:
            if not in_window(item.get("pay_time") or item.get("created_at"), start, end):
                continue
            shop_id = int(item.get("shop_id") or 0)
            if not shop_id:
                continue
            summary[shop_id]["member_stored_orders"] += 1
            summary[shop_id]["member_stored_amount"] += parse_amount_text(item.get("stored_amount_text"))

    return dict(summary)


def parent_order_shop_map(conn, target_date: str):
    start, end = business_window(target_date)
    mapping = {}
    rows = conn.execute(
        """
        SELECT raw_json FROM raw_openapi_mobile_consume
        UNION ALL
        SELECT raw_json FROM raw_openapi_member_consume
        """
    ).fetchall()
    for row in rows:
        data = json.loads(row["raw_json"] or "{}")
        consume = data.get("consume_info", data)
        for key in ("parent_order_info", "order_info"):
            for item in consume.get(key, []) or []:
                event_time = item.get("pay_time") or item.get("created_at") or item.get("room_start_time")
                if not in_window(event_time, start, end):
                    continue
                parent_order_id = item.get("parent_order_id")
                shop_id = item.get("shop_id")
                if parent_order_id and shop_id:
                    mapping[int(parent_order_id)] = int(shop_id)

    rows = conn.execute(
        """
        SELECT parent_order_id, shop_name FROM raw_openapi_preorders
        WHERE parent_order_id IS NOT NULL
          AND arrival_time >= ? AND arrival_time < ?
        """,
        (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
    ).fetchall()
    store_names = load_store_names(conn)
    name_to_shop_id = {name: shop_id for shop_id, name in store_names.items()}
    for row in rows:
        shop_id = name_to_shop_id.get(row["shop_name"])
        if row["parent_order_id"] and shop_id:
            mapping[int(row["parent_order_id"])] = shop_id
    return mapping


def parent_detail_summary(conn, target_date: str):
    start, end = business_window(target_date)
    mapping = parent_order_shop_map(conn, target_date)
    summary = defaultdict(lambda: {
        "detail_room_orders": 0,
        "detail_room_amount": 0.0,
        "detail_product_orders": 0,
        "detail_product_amount": 0.0,
        "detail_product_items": 0,
    })
    rows = conn.execute("SELECT parent_order_id, raw_json FROM raw_openapi_parent_order_details").fetchall()
    for row in rows:
        parent_order_id = int(row["parent_order_id"])
        shop_id = mapping.get(parent_order_id)
        if not shop_id:
            continue
        data = json.loads(row["raw_json"] or "{}")
        orders = data.get("orders", []) if isinstance(data, dict) else []
        for order in orders:
            event_time = order.get("room_start_time")
            if event_time and event_time != "1000-01-01 00:00:00" and not in_window(event_time, start, end):
                continue
            order_type = int(order.get("order_type") or 0)
            paid_amount = float(order.get("paid_amount") or 0) / 100
            refund_amount = float(order.get("refund_amount") or 0) / 100
            net_amount = paid_amount - refund_amount
            if order_type in (0, 1, 2):
                summary[shop_id]["detail_room_orders"] += 1
                summary[shop_id]["detail_room_amount"] += net_amount
            elif order_type in (3, 4, 5, 6, 7, 8):
                summary[shop_id]["detail_product_orders"] += 1
                summary[shop_id]["detail_product_amount"] += net_amount
                for item in order.get("items", []) or []:
                    summary[shop_id]["detail_product_items"] += int(item.get("num") or 0) - int(item.get("refund_num") or 0)
    return dict(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="从 OpenAPI raw 表构建每日验证指标")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    args = parser.parse_args()

    conn = get_connection()
    try:
        store_names = load_store_names(conn)
        marketing = marketing_summary(conn, args.target_date)
        consumes = consume_summary(conn, args.target_date)
        details = parent_detail_summary(conn, args.target_date)
    finally:
        conn.close()

    shop_ids = sorted(set(marketing) | set(consumes) | set(details))
    print(f"OpenAPI raw 清洗验证: {args.target_date}")
    print("shop_id\t门店\t团购订单\t团购净额(分)\t会员开台\t会员开台额(元)\t会员点单\t会员点单额(元)\t会员储值\t会员储值额(元)\t详情房费额(元)\t详情商品额(元)\t详情商品件数")
    for shop_id in shop_ids:
        m = marketing.get(shop_id, {})
        c = consumes.get(shop_id, {})
        d = details.get(shop_id, {})
        print(
            f"{shop_id}\t{store_names.get(shop_id, '')}\t"
            f"{m.get('marketing_orders', 0)}\t{m.get('marketing_net_amount', 0):.0f}\t"
            f"{c.get('member_room_orders', 0)}\t{c.get('member_room_amount', 0):.2f}\t"
            f"{c.get('member_product_orders', 0)}\t{c.get('member_product_amount', 0):.2f}\t"
            f"{c.get('member_stored_orders', 0)}\t{c.get('member_stored_amount', 0):.2f}\t"
            f"{d.get('detail_room_amount', 0):.2f}\t{d.get('detail_product_amount', 0):.2f}\t"
            f"{d.get('detail_product_items', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
