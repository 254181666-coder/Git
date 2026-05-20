#!/usr/bin/env python3
"""
探测 OpenAPI 中是否有可用于日报同步的订单/商品候选接口。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Client, Fun360Credentials


def summarize(payload):
    data = payload.get("data")
    if isinstance(data, dict):
        res = data.get("res", data)
        if isinstance(res, dict):
            rows = res.get("rows")
            if isinstance(rows, list):
                return f"rows={len(rows)} count={res.get('count')} keys={list(res.keys())[:8]}"
            if isinstance(res.get("list"), list):
                return f"list={len(res.get('list'))} keys={list(res.keys())[:8]}"
            return f"res_keys={list(res.keys())[:12]}"
    return f"data_type={type(data).__name__}"


def first_row(payload):
    data = payload.get("data")
    if isinstance(data, dict):
        res = data.get("res", data)
        if isinstance(res, dict) and isinstance(res.get("rows"), list) and res["rows"]:
            row = res["rows"][0]
            preview = {}
            for key in list(row.keys())[:14]:
                value = row[key]
                if key in {"mobile", "phone", "open_id", "union_id", "nickname"}:
                    value = "***"
                preview[key] = value
            return preview
    return None


def main() -> int:
    client = Fun360Client(Fun360Credentials.from_env())
    start = "2026-05-17 08:00:00"
    end = "2026-05-18 08:00:00"
    probes = [
        ("/open/order/drink_list", {"member_id": 0, "status": [1], "pay_status": [1], "page": 1, "page_size": 5}),
        ("/open/order/drink_list", {"shop_id": 348, "start_time": start, "end_time": end, "status": [1], "pay_status": [1], "page": 1, "page_size": 5}),
        ("/open/order/room_list", {"member_id": 0, "status": [1], "pay_status": [1], "page": 1, "page_size": 5}),
        ("/open/order/room_list", {"shop_id": 348, "start_time": start, "end_time": end, "status": [1], "pay_status": [1], "page": 1, "page_size": 5}),
        ("/open/product/paging", {"shop_id": 348, "page": 1, "page_size": 5}),
        ("/open/product/category_list", {"shop_id": 348}),
        ("/open/order/product/get_list", {"shop_id": 348, "start_time": start, "end_time": end, "page": 1, "page_size": 5}),
        ("/open/order/product/get_category_list", {"shop_id": 348, "start_time": start, "end_time": end}),
        ("/open/report/filter/brand_shop", {}),
        ("/open/report/member/get_list", {"start_time": start, "end_time": end, "page": 1, "page_size": 5}),
        ("/open/marketing/orders", {"shop_id": 348, "start_time": start, "end_time": end, "page": 1, "page_size": 5}),
        ("/open/stored_free/orders", {"shop_id": 348, "start_time": start, "end_time": end, "page": 1, "page_size": 5}),
    ]
    for path, body in probes:
        try:
            payload = client.post(path, body)
        except Exception as exc:
            print(f"{path}: ERROR {str(exc)[:180]}")
            continue
        print(f"{path}: code={payload.get('code')} sub={payload.get('sub_code')} msg={payload.get('msg')} {summarize(payload)}")
        row = first_row(payload)
        if row:
            print(f"  first_row={row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
