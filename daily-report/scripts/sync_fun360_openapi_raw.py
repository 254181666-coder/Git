#!/usr/bin/env python3
"""
同步 Fun360 OpenAPI 明细数据到 raw 表。

先用于小范围验证，再逐步扩大到全量自动化。
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.init_sqlite import main as init_sqlite
from scripts.sync_fun360_shops import upsert_shop
from src.database import get_connection
from src.fun360_api import Fun360Client, Fun360Credentials


def business_window(target_date: str):
    start = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=8, minute=0, second=0)
    end = start + timedelta(days=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def rows_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data", {})
    if isinstance(data, dict):
        for container in (data.get("res"), data):
            if isinstance(container, dict) and isinstance(container.get("rows"), list):
                return [row for row in container["rows"] if isinstance(row, dict)]
    return []


def total_from_payload(payload: Dict[str, Any]) -> Optional[int]:
    data = payload.get("data", {})
    if isinstance(data, dict):
        for container in (data.get("res"), data):
            if isinstance(container, dict):
                total = container.get("count")
                if total is not None:
                    return int(total)
    return None


def number(row: Dict[str, Any], keys: Iterable[str], default: float = 0) -> float:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
    return default


def sync_shops(conn, client: Fun360Client) -> int:
    shops = client.shop_list(shop_id=0)
    for shop in shops:
        upsert_shop(conn, shop)
    conn.commit()
    return len(shops)


def sync_products(conn, client: Fun360Client, shop_ids: List[int], page_size: int) -> int:
    total_rows = 0
    for shop_id in shop_ids:
        page = 1
        while True:
            payload = client.post(
                "/open/product/paging",
                {"shop_id": shop_id, "page": page, "page_size": page_size},
            )
            if payload.get("code") != 200:
                raise RuntimeError(f"/open/product/paging 失败: shop_id={shop_id} {payload}")
            rows = rows_from_payload(payload)
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO raw_openapi_products (
                        product_id, shop_id, category_id, category_name, product_name,
                        sale_price, status, raw_json, synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(product_id, shop_id) DO UPDATE SET
                        category_id = excluded.category_id,
                        category_name = excluded.category_name,
                        product_name = excluded.product_name,
                        sale_price = excluded.sale_price,
                        status = excluded.status,
                        raw_json = excluded.raw_json,
                        synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        row.get("product_id"),
                        row.get("shop_id") or shop_id,
                        row.get("category_id"),
                        row.get("category_name"),
                        row.get("name") or row.get("product_name"),
                        number(row, ("sale_price", "price")),
                        row.get("status"),
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
            conn.commit()
            total_rows += len(rows)
            total = total_from_payload(payload)
            if not rows or len(rows) < page_size or (total and page * page_size >= total):
                break
            page += 1
    return total_rows


def sync_marketing_orders(conn, client: Fun360Client, target_date: str, shop_ids: List[int], page_size: int) -> int:
    total_rows = 0
    for shop_id in shop_ids:
        page = 1
        while True:
            payload = client.post(
                "/open/marketing/orders",
                {
                    "shop_id": shop_id,
                    "start_date": target_date,
                    "end_date": target_date,
                    "status": 2,
                    "page": page,
                    "page_size": page_size,
                },
            )
            if payload.get("code") != 200:
                raise RuntimeError(f"/open/marketing/orders 失败: shop_id={shop_id} {payload}")
            rows = rows_from_payload(payload)
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO raw_openapi_marketing_orders (
                        order_id, shop_id, mobile, biz_day, status, pay_status,
                        paid_amount, refund_amount, raw_json, synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(order_id) DO UPDATE SET
                        shop_id = excluded.shop_id,
                        mobile = excluded.mobile,
                        biz_day = excluded.biz_day,
                        status = excluded.status,
                        pay_status = excluded.pay_status,
                        paid_amount = excluded.paid_amount,
                        refund_amount = excluded.refund_amount,
                        raw_json = excluded.raw_json,
                        synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        row.get("order_id"),
                        row.get("shop_id"),
                        row.get("mobile"),
                        row.get("biz_day"),
                        row.get("status"),
                        row.get("pay_status"),
                        number(row, ("paid_amount",)),
                        number(row, ("refund_amount",)),
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
            conn.commit()
            total_rows += len(rows)
            total = total_from_payload(payload)
            if not rows or len(rows) < page_size or (total and page * page_size >= total):
                break
            page += 1
    return total_rows


def sync_preorders(conn, client: Fun360Client, target_date: str, shop_ids: List[int]) -> int:
    start, end = business_window(target_date)
    payload = client.post(
        "/open/order/preorders",
        {"start_time": start, "end_time": end, "shop_ids": shop_ids},
    )
    if payload.get("code") != 200:
        raise RuntimeError(f"/open/order/preorders 失败: {payload}")
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    for row in rows:
        conn.execute(
            """
            INSERT INTO raw_openapi_preorders (
                preorder_id, order_id, parent_order_id, shop_name, preorder_mobile,
                arrival_time, status, preorder_status, raw_json, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(preorder_id, order_id) DO UPDATE SET
                parent_order_id = excluded.parent_order_id,
                shop_name = excluded.shop_name,
                preorder_mobile = excluded.preorder_mobile,
                arrival_time = excluded.arrival_time,
                status = excluded.status,
                preorder_status = excluded.preorder_status,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            (
                row.get("preorder_id"),
                str(row.get("order_id") or ""),
                row.get("parent_order_id"),
                row.get("shop_name"),
                row.get("preorder_mobile"),
                row.get("arrival_time"),
                row.get("status"),
                row.get("preorder_status"),
                json.dumps(row, ensure_ascii=False),
            ),
        )
    conn.commit()
    return len(rows)


def sync_members(conn, client: Fun360Client, max_pages: int, page_size: int) -> List[Dict[str, Any]]:
    synced: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        payload = client.post(
            "/open/member/list",
            {
                "page": page,
                "page_size": page_size,
                "register_shop_id": -1,
                "mobile": "",
                "coupon_cnt": 0,
                "wallet_cnt": 0,
                "deposit_cnt": 0,
                "stored_cnt": 0,
            },
        )
        if payload.get("code") != 200:
            raise RuntimeError(f"/open/member/list 失败: page={page} {payload}")
        rows = rows_from_payload(payload)
        for row in rows:
            conn.execute(
                """
                INSERT INTO raw_openapi_members (
                    member_id, mobile, username, register_shop_id, register_at,
                    status, raw_json, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(member_id) DO UPDATE SET
                    mobile = excluded.mobile,
                    username = excluded.username,
                    register_shop_id = excluded.register_shop_id,
                    register_at = excluded.register_at,
                    status = excluded.status,
                    raw_json = excluded.raw_json,
                    synced_at = CURRENT_TIMESTAMP
                """,
                (
                    row.get("member_id"),
                    row.get("mobile"),
                    row.get("username"),
                    row.get("register_shop_id"),
                    row.get("register_at"),
                    row.get("status"),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
        conn.commit()
        synced.extend(rows)
        if not rows or len(rows) < page_size:
            break
    return synced


def sync_member_consumes(conn, client: Fun360Client, members: List[Dict[str, Any]], limit: int, only_missing: bool) -> int:
    count = 0
    for row in members:
        if limit and count >= limit:
            break
        member_id = row.get("member_id")
        mobile = row.get("mobile")
        if not member_id or not mobile:
            continue
        if only_missing:
            exists = conn.execute(
                "SELECT 1 FROM raw_openapi_member_consume WHERE member_id = ?",
                (member_id,),
            ).fetchone()
            if exists:
                continue
        try:
            payload = client.post(
                "/open/private_marketing/user/detail",
                {"mobile": mobile, "info_key": "consume"},
            )
        except Exception as exc:
            print(f"  会员画像跳过: member_id={member_id} error={str(exc)[:120]}")
            continue
        if payload.get("code") != 200:
            print(f"  会员画像跳过: member_id={member_id} code={payload.get('code')} msg={payload.get('msg')}")
            continue
        conn.execute(
            """
            INSERT INTO raw_openapi_member_consume (member_id, mobile, raw_json, synced_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(member_id) DO UPDATE SET
                mobile = excluded.mobile,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            (member_id, mobile, json.dumps(payload.get("data", {}), ensure_ascii=False)),
        )
        conn.commit()
        count += 1
        if count % 10 == 0:
            print(f"  会员消费画像已同步: {count}")
    return count


def sync_mobile_consumes(conn, client: Fun360Client, mobiles: List[str], limit: int, only_missing: bool) -> int:
    count = 0
    for mobile in mobiles:
        if limit and count >= limit:
            break
        if not mobile:
            continue
        if only_missing:
            exists = conn.execute(
                "SELECT 1 FROM raw_openapi_mobile_consume WHERE mobile = ?",
                (mobile,),
            ).fetchone()
            if exists:
                continue
        try:
            payload = client.post(
                "/open/private_marketing/user/detail",
                {"mobile": mobile, "info_key": "consume"},
            )
        except Exception as exc:
            print(f"  手机画像跳过: mobile={mobile[:3]}****{mobile[-4:]} error={str(exc)[:120]}")
            continue
        if payload.get("code") != 200:
            print(f"  手机画像跳过: mobile={mobile[:3]}****{mobile[-4:]} code={payload.get('code')} msg={payload.get('msg')}")
            continue
        data = payload.get("data", {}) or {}
        base_info = data.get("base_info", {}) if isinstance(data, dict) else {}
        member_id = base_info.get("member_id") or None
        conn.execute(
            """
            INSERT INTO raw_openapi_mobile_consume (mobile, member_id, raw_json, synced_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(mobile) DO UPDATE SET
                member_id = excluded.member_id,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            (mobile, member_id, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
        count += 1
        if count % 10 == 0:
            print(f"  手机消费画像已同步: {count}")
    return count


def parent_order_ids_from_raw(conn, target_date: str) -> List[int]:
    start, end = business_window(target_date)
    ids = set()
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
                if not event_time or not (start <= event_time < end):
                    continue
                parent_order_id = item.get("parent_order_id")
                if parent_order_id:
                    ids.add(int(parent_order_id))

    rows = conn.execute(
        """
        SELECT parent_order_id FROM raw_openapi_preorders
        WHERE parent_order_id IS NOT NULL
          AND arrival_time >= ? AND arrival_time < ?
        """,
        (start, end),
    ).fetchall()
    ids.update(int(row["parent_order_id"]) for row in rows if row["parent_order_id"])
    return sorted(ids)


def sync_parent_order_details(conn, client: Fun360Client, parent_order_ids: List[int], limit: int, only_missing: bool) -> int:
    count = 0
    for parent_order_id in parent_order_ids:
        if limit and count >= limit:
            break
        if only_missing:
            exists = conn.execute(
                "SELECT 1 FROM raw_openapi_parent_order_details WHERE parent_order_id = ?",
                (parent_order_id,),
            ).fetchone()
            if exists:
                continue
        try:
            payload = client.post("/open/parent_order/detail", {"parent_order_id": parent_order_id})
        except Exception as exc:
            print(f"  开台单详情跳过: parent_order_id={parent_order_id} error={str(exc)[:120]}")
            continue
        if payload.get("code") != 200:
            print(f"  开台单详情跳过: parent_order_id={parent_order_id} code={payload.get('code')} msg={payload.get('msg')}")
            continue
        conn.execute(
            """
            INSERT INTO raw_openapi_parent_order_details (parent_order_id, raw_json, synced_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(parent_order_id) DO UPDATE SET
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            (parent_order_id, json.dumps(payload.get("data", {}), ensure_ascii=False)),
        )
        conn.commit()
        count += 1
        if count % 10 == 0:
            print(f"  开台单详情已同步: {count}")
    return count


def active_mobiles(conn, target_date: str) -> List[str]:
    start, end = business_window(target_date)
    rows = conn.execute(
        """
        SELECT mobile FROM raw_openapi_marketing_orders
        WHERE biz_day = ? AND mobile IS NOT NULL AND mobile <> ''
        UNION
        SELECT preorder_mobile AS mobile FROM raw_openapi_preorders
        WHERE preorder_mobile IS NOT NULL AND preorder_mobile <> ''
          AND arrival_time >= ? AND arrival_time < ?
        """,
        (target_date, start, end),
    ).fetchall()
    return [str(row["mobile"]) for row in rows]


def selected_shop_ids(conn, shop_id: Optional[int]) -> List[int]:
    if shop_id:
        return [shop_id]
    rows = conn.execute(
        "SELECT fun360_shop_id FROM stores WHERE fun360_shop_id IS NOT NULL AND store_name <> '总部' ORDER BY id"
    ).fetchall()
    return [int(row["fun360_shop_id"]) for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 Fun360 OpenAPI raw 明细")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    parser.add_argument("--shop-id", type=int, help="只同步单个 shop_id")
    parser.add_argument("--member-pages", type=int, default=1, help="同步会员页数，默认 1")
    parser.add_argument("--consume-limit", type=int, default=10, help="同步会员消费画像数量，默认 10")
    parser.add_argument("--page-size", type=int, default=50, help="分页大小，默认 50")
    parser.add_argument("--timeout", type=int, default=90, help="接口超时时间秒，默认 90")
    parser.add_argument("--skip-products", action="store_true", help="跳过商品档案同步")
    parser.add_argument("--skip-marketing", action="store_true", help="跳过团购/卡券订单同步")
    parser.add_argument("--skip-preorders", action="store_true", help="跳过预订单同步")
    parser.add_argument("--skip-members", action="store_true", help="跳过会员列表同步")
    parser.add_argument("--skip-consumes", action="store_true", help="跳过会员消费画像同步")
    parser.add_argument("--sync-parent-details", action="store_true", help="同步当天相关开台单详情")
    parser.add_argument("--parent-detail-limit", type=int, default=0, help="开台单详情同步数量上限，0 不限制")
    parser.add_argument("--consume-only-missing", action="store_true", help="只同步尚未落库的会员消费画像")
    parser.add_argument("--consume-active-mobiles", action="store_true", help="按当天团购/预订手机号同步消费画像")
    args = parser.parse_args()

    start, end = business_window(args.target_date)
    init_sqlite()
    client = Fun360Client(Fun360Credentials.from_env(), timeout=args.timeout)

    conn = get_connection()
    try:
        shop_count = sync_shops(conn, client)
        shop_ids = selected_shop_ids(conn, args.shop_id)
        print(f"门店同步: {shop_count} 家，本次处理 shop_id={shop_ids}")
        print(f"营业窗口: {start} ~ {end}")

        if args.skip_products:
            print("商品档案: 跳过")
        else:
            product_count = sync_products(conn, client, shop_ids, args.page_size)
            print(f"商品档案: {product_count} 行")

        if args.skip_marketing:
            print("团购/卡券订单: 跳过")
        else:
            marketing_count = sync_marketing_orders(conn, client, args.target_date, shop_ids, args.page_size)
            print(f"团购/卡券订单: {marketing_count} 行")

        if args.skip_preorders:
            print("预订单: 跳过")
        else:
            preorder_count = sync_preorders(conn, client, args.target_date, shop_ids)
            print(f"预订单: {preorder_count} 行")

        if args.skip_members:
            members = [
                dict(row) for row in conn.execute(
                    "SELECT member_id, mobile FROM raw_openapi_members ORDER BY member_id DESC LIMIT ?",
                    (args.member_pages * args.page_size,),
                ).fetchall()
            ]
            print(f"会员列表: 跳过接口，使用本地 {len(members)} 行")
        else:
            members = sync_members(conn, client, args.member_pages, args.page_size)
            print(f"会员列表: {len(members)} 行")

        if args.skip_consumes:
            print("会员消费画像: 跳过")
        elif args.consume_active_mobiles:
            mobiles = active_mobiles(conn, args.target_date)
            print(f"活跃手机号: {len(mobiles)} 个")
            consume_count = sync_mobile_consumes(conn, client, mobiles, args.consume_limit, args.consume_only_missing)
            print(f"手机消费画像: {consume_count} 个")
        else:
            consume_count = sync_member_consumes(conn, client, members, args.consume_limit, args.consume_only_missing)
            print(f"会员消费画像: {consume_count} 个")

        if args.sync_parent_details:
            parent_order_ids = parent_order_ids_from_raw(conn, args.target_date)
            print(f"当天相关开台单: {len(parent_order_ids)} 个")
            detail_count = sync_parent_order_details(
                conn, client, parent_order_ids, args.parent_detail_limit, args.consume_only_missing
            )
            print(f"开台单详情: {detail_count} 个")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
