#!/usr/bin/env python3
"""
验证 Fun360 /open/shop/list 接口。

需要先设置:
  FUN360_APPID
  FUN360_SECRET
  FUN360_TOKEN 可选
  FUN360_AUTHORIZATION 可选
  FUN360_PHASE 可选，默认 production
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Client, Fun360ConfigError, Fun360Credentials


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

    print(f"请求成功，门店数: {len(shops)}")
    for shop in shops[:10]:
        print(json.dumps({
            "shop_id": shop.get("shop_id"),
            "name": shop.get("name"),
            "address": shop.get("address"),
            "is_online": shop.get("is_online"),
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
