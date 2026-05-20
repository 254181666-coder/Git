"""
Fun360 open-api 客户端。
"""
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import FUN360_BASE_URL, FUN360_DEFAULT_PHASE


class Fun360ConfigError(RuntimeError):
    pass


def load_local_env():
    """Load local .env files without overriding existing environment values."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for filename in (".env.local", ".env"):
        path = os.path.join(project_root, filename)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


@dataclass
class Fun360Credentials:
    appid: str
    secret: str
    token: str = ""
    authorization: str = ""
    phase: str = FUN360_DEFAULT_PHASE

    @classmethod
    def from_env(cls):
        load_local_env()
        missing = [
            name for name in ("FUN360_APPID", "FUN360_SECRET")
            if not os.getenv(name)
        ]
        if missing:
            raise Fun360ConfigError(
                "缺少环境变量: " + ", ".join(missing)
            )
        return cls(
            appid=os.environ["FUN360_APPID"],
            secret=os.environ["FUN360_SECRET"],
            token=os.getenv("FUN360_TOKEN", ""),
            authorization=os.getenv("FUN360_AUTHORIZATION", ""),
            phase=os.getenv("FUN360_PHASE", FUN360_DEFAULT_PHASE),
        )


class Fun360Client:
    def __init__(self, credentials: Fun360Credentials, base_url: str = FUN360_BASE_URL, timeout: int = 30):
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def make_sign(timestamp: int, nonce: str, secret: str) -> str:
        raw = f"nonce={nonce}&secret={secret}&timestamp={timestamp}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = body or {}
        timestamp = int(time.time())
        nonce = uuid.uuid4().hex
        query = {
            "appid": self.credentials.appid,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": self.make_sign(timestamp, nonce, self.credentials.secret),
        }
        url = f"{self.base_url}{path}?{urlencode(query)}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "UUID": str(uuid.uuid4()),
            "PHASE": self.credentials.phase,
            "DEVICE-PLATFORM": "IOS",
            "DEVICE-VERSION": "15.2",
            "APP-PLATFORM": "wx_mini_app",
            "APP-VERSION": "1.4.5",
            "APPID": self.credentials.appid,
        }
        if self.credentials.token:
            headers["TOKEN"] = self.credentials.token
        if self.credentials.authorization:
            headers["Authorization"] = self._authorization_header()
        req = Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Fun360 HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Fun360 请求失败: {exc.reason}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Fun360 返回非JSON内容: {payload[:300]}") from exc

    def shop_list(self, shop_id: int = 0):
        data = self.post("/open/shop/list", {"shop_id": shop_id})
        if data.get("code") != 200:
            raise RuntimeError(f"Fun360业务错误: {data}")
        return data.get("data", {}).get("res", []) or []

    def _authorization_header(self) -> str:
        value = self.credentials.authorization.strip()
        if value.lower().startswith("bearer "):
            return value
        return f"Bearer {value}"
