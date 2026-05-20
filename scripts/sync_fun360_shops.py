#!/usr/bin/env python3
"""
从 Fun360 /open/shop/list 同步门店到本地SQLite。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection
from src.fun360_api import Fun360Client, Fun360ConfigError, Fun360Credentials
from scripts.init_sqlite import main as init_sqlite


def upsert_shop(conn, shop):
    sql = """
        INSERT INTO stores (
            store_name, fun360_shop_id, image, images, address, lng, lat,
            opening_phone, opening_hours, province, city, district, is_online,
            tags, raw_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(fun360_shop_id) DO UPDATE SET
            store_name = excluded.store_name,
            image = excluded.image,
            images = excluded.images,
            address = excluded.address,
            lng = excluded.lng,
            lat = excluded.lat,
            opening_phone = excluded.opening_phone,
            opening_hours = excluded.opening_hours,
            province = excluded.province,
            city = excluded.city,
            district = excluded.district,
            is_online = excluded.is_online,
            tags = excluded.tags,
            raw_json = excluded.raw_json,
            updated_at = CURRENT_TIMESTAMP
    """
    conn.execute(sql, (
        shop.get("name") or f"shop_{shop.get('shop_id')}",
        shop.get("shop_id"),
        shop.get("image"),
        shop.get("images"),
        shop.get("address"),
        shop.get("lng"),
        shop.get("lat"),
        shop.get("opening_phone"),
        shop.get("opening_hours"),
        shop.get("province"),
        shop.get("city"),
        shop.get("district"),
        shop.get("is_online"),
        json.dumps(shop.get("tags", []), ensure_ascii=False),
        json.dumps(shop, ensure_ascii=False),
    ))


def main():
    try:
        client = Fun360Client(Fun360Credentials.from_env())
        shops = client.shop_list(shop_id=0)
    except Fun360ConfigError as exc:
        print(f"配置不完整: {exc}")
        return 2
    except Exception as exc:
        print(f"请求失败: {exc}")
        return 1

    init_sqlite()
    conn = get_connection()
    try:
        for shop in shops:
            upsert_shop(conn, shop)
        conn.commit()
    finally:
        conn.close()

    print(f"已同步门店: {len(shops)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
