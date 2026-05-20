#!/usr/bin/env python3
"""
探测预订/第三方预订接口是否可按门店营业日拉取。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Client, Fun360Credentials


def summarize(payload):
    data = payload.get("data")
    if isinstance(data, list):
        return f"list={len(data)} first_keys={list(data[0].keys())[:12] if data else []}"
    if isinstance(data, dict):
        rows = data.get("rows") or data.get("res", {}).get("rows")
        if isinstance(rows, list):
            return f"rows={len(rows)} count={data.get('count')} first_keys={list(rows[0].keys())[:12] if rows else []}"
        return f"data_keys={list(data.keys())[:12]}"
    return f"data_type={type(data).__name__}"


def main() -> int:
    client = Fun360Client(Fun360Credentials.from_env(), timeout=120)
    shop_ids = [348, 349, 624]
    start = "2026-05-17 08:00:00"
    end = "2026-05-18 08:00:00"
    probes = [
        ("/open/order/preorders", {"start_time": start, "end_time": end, "shop_ids": shop_ids}),
        ("/open/preorder/mt_dy/list", {"brand_id": 0, "shop_id": 348, "page": 1, "page_size": 50, "biz_start_day": "2026-05-17", "biz_end_day": "2026-05-17"}),
        ("/open/preorder/mt_dy/list", {"brand_id": 34, "shop_id": 348, "page": 1, "page_size": 50, "biz_start_day": "2026-05-17", "biz_end_day": "2026-05-17"}),
    ]
    for path, body in probes:
        try:
            payload = client.post(path, body)
        except Exception as exc:
            print(f"{path}: ERROR {str(exc)[:200]}")
            continue
        print(f"{path}: code={payload.get('code')} sub={payload.get('sub_code')} msg={payload.get('msg')} {summarize(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
