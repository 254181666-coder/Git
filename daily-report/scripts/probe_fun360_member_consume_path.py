#!/usr/bin/env python3
"""
验证“会员列表 -> 用户消费画像”是否可作为明细数据来源。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Client, Fun360Credentials


def main() -> int:
    client = Fun360Client(Fun360Credentials.from_env())
    members = client.post(
        "/open/member/list",
        {
            "page": 1,
            "page_size": 5,
            "register_shop_id": -1,
            "mobile": "",
            "coupon_cnt": 0,
            "wallet_cnt": 0,
            "deposit_cnt": 0,
            "stored_cnt": 0,
        },
    )
    res = members.get("data", {}).get("res", {})
    rows = res.get("rows", [])
    print(f"member/list code={members.get('code')} count={res.get('count')} rows={len(rows)}")
    if not rows:
        return 0

    row = rows[0]
    mobile = row.get("mobile")
    print(f"sample member_id={row.get('member_id')} has_mobile={bool(mobile)}")
    if not mobile:
        return 0

    detail = client.post(
        "/open/private_marketing/user/detail",
        {"mobile": mobile, "info_key": "consume"},
    )
    data = detail.get("data", {})
    consume = data.get("consume_info", {})
    print(f"consume/detail code={detail.get('code')} keys={list(consume.keys())}")
    for key in ("parent_order_info", "order_info", "stored_info"):
        value = consume.get(key)
        print(f"{key}: {len(value) if isinstance(value, list) else type(value).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
