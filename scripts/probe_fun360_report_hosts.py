#!/usr/bin/env python3
"""
探测 Fun360 后台报表接口所在域名。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Client, Fun360Credentials


CANDIDATE_BASE_URLS = [
    "https://open-api.fun360.cn",
    "https://open-api-dev.pub.fun360.cn",
    "https://ktv.fun360.cn",
    "https://ktv-dev.pub.fun360.cn",
    "https://op.fun360.cn",
    "https://op-dev.pub.fun360.cn",
    "https://api.fun360.cn",
    "https://api-dev.pub.fun360.cn",
]


def main() -> int:
    credentials = Fun360Credentials.from_env()
    for base_url in CANDIDATE_BASE_URLS:
        client = Fun360Client(credentials, base_url=base_url, timeout=8)
        try:
            payload = client.post("/api/report/filter/brand_shop", {})
        except Exception as exc:
            text = str(exc).replace("\n", " ")
            print(f"{base_url} -> ERROR {text[:180]}")
            continue
        code = payload.get("code")
        keys = ",".join(payload.keys())
        print(f"{base_url} -> OK code={code} keys={keys} sample={str(payload)[:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
