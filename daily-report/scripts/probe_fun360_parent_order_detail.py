#!/usr/bin/env python3
"""
从已同步消费画像中抽一个 parent_order_id，验证 /open/parent_order/detail。
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection
from src.fun360_api import Fun360Client, Fun360Credentials


def find_parent_order_id():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT raw_json FROM raw_openapi_mobile_consume
            UNION ALL
            SELECT raw_json FROM raw_openapi_member_consume
            LIMIT 400
            """
        ).fetchall()
    finally:
        conn.close()
    for row in rows:
        data = json.loads(row["raw_json"] or "{}")
        consume = data.get("consume_info", data)
        for key in ("parent_order_info", "order_info"):
            for item in consume.get(key, []) or []:
                parent_order_id = item.get("parent_order_id")
                if parent_order_id:
                    return int(parent_order_id)
    return None


def main() -> int:
    parent_order_id = find_parent_order_id()
    if not parent_order_id:
        print("no parent_order_id")
        return 1
    client = Fun360Client(Fun360Credentials.from_env(), timeout=120)
    payload = client.post("/open/parent_order/detail", {"parent_order_id": parent_order_id})
    print(f"parent_order_id={parent_order_id} code={payload.get('code')} msg={payload.get('msg')}")
    orders = payload.get("data", {}).get("orders", [])
    print(f"orders={len(orders)}")
    if orders:
        first = orders[0]
        print(f"order_keys={list(first.keys())[:16]}")
        items = first.get("items") or []
        print(f"items={len(items)} first_item={items[0] if items else {}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
