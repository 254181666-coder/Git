#!/usr/bin/env python3
"""
探测后台报表接口需要的认证 Header 形式。
不会打印任何凭证内容。
"""
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fun360_api import Fun360Credentials


BASE_URL = "https://ktv.fun360.cn"
PATH = "/api/report/filter/brand_shop"


def request_with_headers(name, headers):
    url = f"{BASE_URL}{PATH}"
    req = Request(
        url,
        data=json.dumps({}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "PHASE": os.getenv("FUN360_PHASE", "production"),
            "DEVICE-PLATFORM": "IOS",
            "DEVICE-VERSION": "15.2",
            "APP-PLATFORM": "cashier",
            "APP-VERSION": "1.4.5",
            "APPID": os.getenv("FUN360_APPID", ""),
            **headers,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").replace("\n", " ")
        print(f"{name}: HTTP {exc.code} {body[:160]}")
        return
    except URLError as exc:
        print(f"{name}: URLERROR {exc.reason}")
        return
    print(f"{name}: code={payload.get('code')} sub_code={payload.get('sub_code')} msg={payload.get('msg')}")


def main() -> int:
    credentials = Fun360Credentials.from_env()
    appid = credentials.appid
    secret = credentials.secret
    modes = [
        ("no-token", {}),
        ("token-appid", {"TOKEN": appid}),
        ("token-secret", {"TOKEN": secret}),
        ("bearer-appid", {"Authorization": f"Bearer {appid}"}),
        ("bearer-secret", {"Authorization": f"Bearer {secret}"}),
        ("both-secret", {"TOKEN": secret, "Authorization": f"Bearer {secret}"}),
    ]
    for name, headers in modes:
        request_with_headers(name, headers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
