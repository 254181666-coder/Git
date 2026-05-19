#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json
import os


PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "127.0.0.1")
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "douyin-callback.log"


def append_log(payload):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False, indent=2))
        file.write("\n\n")


def header_value(headers, name):
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.upper())


def headers_to_dict(headers):
    return {key: value for key, value in headers.items()}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._send_json(200, {"ok": True, "service": "douyin-callback-server"})

        if parsed.path in {"/douyin/callback", "/douyin/spi", "/douyin/webhook"}:
            payload = {
                "time": __import__("datetime").datetime.now().isoformat(),
                "method": "GET",
                "path": parsed.path,
                "query": parse_qs(parsed.query),
                "logid": header_value(self.headers, "X-Bytedance-Logid"),
                "client_key": header_value(self.headers, "x-life-clientkey"),
                "sign": header_value(self.headers, "x-life-sign"),
                "headers": headers_to_dict(self.headers),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            try:
                append_log(payload)
            except Exception as error:
                print(f"Failed to write callback log: {error}")
            return self._send_json(200, {"data": {"error_code": 0, "description": "success"}})

        return self._send_json(404, {"ok": False, "message": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        body_text = raw.decode("utf-8", errors="replace")

        if parsed.path not in {"/douyin/callback", "/douyin/spi", "/douyin/webhook"}:
            return self._send_json(404, {"ok": False, "message": "Not found"})

        try:
            body = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            body = body_text

        if isinstance(body, dict):
            challenge = None
            content = body.get("content")
            if isinstance(content, dict):
                challenge = content.get("challenge")
            if challenge is None:
                challenge = body.get("challenge")
            if challenge is not None:
                return self._send_json(200, {"challenge": challenge})

        payload = {
            "time": __import__("datetime").datetime.now().isoformat(),
            "method": "POST",
            "path": parsed.path,
            "query": parse_qs(parsed.query),
            "logid": header_value(self.headers, "X-Bytedance-Logid"),
            "client_key": header_value(self.headers, "x-life-clientkey"),
            "sign": header_value(self.headers, "x-life-sign"),
            "headers": headers_to_dict(self.headers),
            "body": body,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        try:
            append_log(payload)
        except Exception as error:
            print(f"Failed to write callback log: {error}")
        return self._send_json(200, {"data": {"error_code": 0, "description": "success"}})

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Douyin callback server listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
