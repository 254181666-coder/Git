#!/usr/bin/env python3
"""
按营业日从 Fun360 同步日报所需数据到本地 SQLite。

用法:
    python3 scripts/sync_fun360_daily_data.py 2026-05-17

营业日口径: 当日 08:00:00 到次日 08:00:00。
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.init_sqlite import main as init_sqlite
from src.config import BIG_CATEGORIES, CATEGORY_MAP, FUN360_REPORT_BASE_URL
from src.database import get_connection
from src.fun360_api import Fun360Client, Fun360ConfigError, Fun360Credentials


BRAND_NAME = "华庭娱乐"
DEFAULT_PAGE_SIZE = 200


def business_window(target_date: str) -> Tuple[str, str]:
    start = datetime.strptime(target_date, "%Y-%m-%d").replace(hour=8, minute=0, second=0)
    end = start + timedelta(days=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("list", "rows", "res", "data", "items", "records"):
            if isinstance(value.get(key), list):
                return value[key]
    return []


def first_number(row: Dict[str, Any], keys: Iterable[str], default: float = 0) -> float:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            try:
                return float(str(value).replace(",", "").replace("¥", ""))
            except ValueError:
                continue
    return default


def first_text(row: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def big_category(category: str) -> str:
    return CATEGORY_MAP.get(category, category if category in BIG_CATEGORIES else "其他")


def get_or_create_store(conn, shop: Dict[str, Any]) -> int:
    shop_id = shop.get("shop_id") or shop.get("id")
    store_name = shop.get("shop_name") or shop.get("name") or f"shop_{shop_id}"
    conn.execute(
        """
        INSERT INTO stores (store_name, fun360_shop_id, raw_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(fun360_shop_id) DO UPDATE SET
            store_name = excluded.store_name,
            raw_json = excluded.raw_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (store_name, shop_id, json.dumps(shop, ensure_ascii=False)),
    )
    row = conn.execute("SELECT id FROM stores WHERE fun360_shop_id = ?", (shop_id,)).fetchone()
    return int(row["id"])


def fetch_brand_shops(client: Fun360Client) -> Tuple[int, List[Dict[str, Any]]]:
    shops = client.shop_list(shop_id=0)
    normalized: List[Dict[str, Any]] = []
    brand_id = 0
    for shop in shops:
        shop_id = shop.get("shop_id") or shop.get("id")
        shop_name = shop.get("shop_name") or shop.get("name")
        if not shop_id or not shop_name:
            continue
        row = dict(shop)
        row["shop_id"] = int(shop_id)
        row["shop_name"] = shop_name
        if row.get("brand_id") and not brand_id:
            brand_id = int(row["brand_id"])
        normalized.append(row)
    shops = normalized
    if not shops:
        raise RuntimeError("未从 /open/shop/list 获取到门店")
    return brand_id, shops


def is_report_endpoint_missing(exc: Exception) -> bool:
    text = str(exc)
    return "HTTP 404" in text and "/api/" not in FUN360_REPORT_BASE_URL


def is_report_token_unauthorized(exc: Exception) -> bool:
    text = str(exc)
    return "Token unauthorized" in text or "99001002" in text


def fetch_paged(client: Fun360Client, path: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page = 1
    while True:
        payload = client.post(path, {**body, "page": page, "page_size": DEFAULT_PAGE_SIZE})
        if payload.get("code") not in (None, 0, 200):
            raise RuntimeError(f"{path} 返回异常: {payload}")
        data = payload.get("data", payload)
        batch = as_list(data)
        rows.extend([row for row in batch if isinstance(row, dict)])
        total = first_number(data, ("total", "count", "total_count"), 0) if isinstance(data, dict) else 0
        if not batch or len(batch) < DEFAULT_PAGE_SIZE or (total and len(rows) >= total):
            break
        page += 1
    return rows


def sync_product_sales(conn, client: Fun360Client, brand_id: int, shop: Dict[str, Any], target_date: str, start: str, end: str) -> int:
    store_id = get_or_create_store(conn, shop)
    shop_id = int(shop["shop_id"])
    conn.execute(
        "DELETE FROM product_sales_summary WHERE store_id = ? AND data_date = ?",
        (store_id, target_date),
    )

    rows = fetch_paged(
        client,
        "/api/order/product/get_list",
        {
            "brand_id": brand_id,
            "shop_id": shop_id,
            "start_time": start,
            "end_time": end,
            "product_name": "",
            "category_id": 0,
            "area_id": 0,
        },
    )
    for row in rows:
        category = first_text(row, ("category_name", "category", "product_category_name"))
        quantity = first_number(row, ("sale_total_num", "quantity", "num", "product_num"), 0)
        amount = first_number(row, ("sale_total_amount", "sales_amount", "amount", "total_amount"), 0)
        conn.execute(
            """
            INSERT INTO product_sales_summary (
                store_id, data_date, product_name, product_code, category, system_category,
                unit, unit_price, quantity, sales_amount, big_category, raw_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                store_id,
                target_date,
                first_text(row, ("product_name", "name")),
                first_text(row, ("product_code", "code", "product_id")),
                category,
                category,
                first_text(row, ("product_unit", "unit")),
                first_number(row, ("unit_price", "price"), 0),
                int(quantity),
                amount,
                big_category(category),
                json.dumps(row, ensure_ascii=False),
            ),
        )
    return len(rows)


def sync_stored_value(conn, client: Fun360Client, brand_id: int, shops_by_id: Dict[int, int], target_date: str, start: str, end: str) -> int:
    conn.execute("DELETE FROM stored_value WHERE data_date = ?", (target_date,))
    rows = fetch_paged(
        client,
        "/api/report/member/get_list",
        {
            "brand_id": brand_id,
            "start_time": start,
            "end_time": end,
            "balance_type": "recharge",
        },
    )

    inserted = 0
    for row in rows:
        shop_id = row.get("shop_id") or row.get("shopId")
        if not shop_id or int(shop_id) not in shops_by_id:
            continue
        store_id = shops_by_id[int(shop_id)]
        amount = first_number(row, ("recharge_amount", "stored_amount", "amount", "balance_change"), 0)
        conn.execute(
            """
            INSERT INTO stored_value (
                store_id, data_date, stored_amount, payment_method, payment_amount,
                recharge_time, external_id, member_name, member_phone, raw_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                store_id,
                target_date,
                amount,
                first_text(row, ("pay_type", "payment_method", "pay_name")),
                first_number(row, ("pay_amount", "payment_amount", "amount"), amount),
                first_text(row, ("recharge_time", "created_at", "pay_time")),
                first_text(row, ("stored_order_id", "order_id", "id")),
                first_text(row, ("member_name", "name")),
                first_text(row, ("member_phone", "phone", "mobile")),
                json.dumps(row, ensure_ascii=False),
            ),
        )
        inserted += 1
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 Fun360 每日报告数据")
    parser.add_argument("target_date", help="数据日期，格式 YYYY-MM-DD")
    args = parser.parse_args()
    target_date = args.target_date
    start, end = business_window(target_date)

    try:
        credentials = Fun360Credentials.from_env()
        client = Fun360Client(credentials)
        report_client = Fun360Client(credentials, base_url=FUN360_REPORT_BASE_URL)
    except Fun360ConfigError as exc:
        print(f"配置不完整: {exc}")
        return 2

    init_sqlite()
    brand_id, shops = fetch_brand_shops(client)
    print(f"品牌: {BRAND_NAME} ({brand_id})，门店数: {len(shops)}，营业日: {start} ~ {end}")

    conn = get_connection()
    try:
        shops_by_id: Dict[int, int] = {}
        for shop in shops:
            shops_by_id[int(shop["shop_id"])] = get_or_create_store(conn, shop)
        conn.commit()

        product_total = 0
        for shop in shops:
            try:
                count = sync_product_sales(conn, report_client, brand_id, shop, target_date, start, end)
            except Exception as exc:
                if is_report_endpoint_missing(exc):
                    print("门店同步成功，但当前 OpenAPI 域名未开放后台报表接口。")
                    print("请配置 FUN360_REPORT_BASE_URL 为包含 /api/report 与 /api/order/product 接口的后台接口域名。")
                    return 3
                if is_report_token_unauthorized(exc):
                    print("门店同步成功，后台报表域名已确认，但缺少有效后台 TOKEN/Authorization。")
                    print("请在 .env.local 中配置 FUN360_TOKEN 或 FUN360_AUTHORIZATION 后重试。")
                    return 4
                raise
            product_total += count
            conn.commit()
            print(f"商品销售: {shop.get('shop_name')} {count} 行")

        stored_total = sync_stored_value(conn, report_client, brand_id, shops_by_id, target_date, start, end)
        conn.commit()
        print(f"会员储值: {stored_total} 行")
    finally:
        conn.close()

    print("同步完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
