#!/usr/bin/env python3
"""Send a daily report to a WeChat conversation on macOS.

This script uses AppleScript/System Events to drive the WeChat desktop app.
It requires WeChat to be installed and Terminal/Python to have Accessibility
permission in System Settings.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from string import Template


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "daily_auto_send.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def setup_logging(config: dict) -> None:
    log_dir = Path(config.get("log_dir", PROJECT_ROOT / "logs")).expanduser()
    if not log_dir.is_absolute():
        log_dir = PROJECT_ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, str(config.get("log_level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "send_to_wechat.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def render_message(template: str, report_path: Path) -> str:
    return Template(template).safe_substitute(
        report_name=report_path.name,
        report_path=str(report_path),
    )


def run_osascript(script: str) -> None:
    result = subprocess.run(
        ["osascript", "-e", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "osascript failed")


def quote_for_applescript(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_send_script(
    recipient: str,
    message: str,
    report_path: Path,
    send_file: bool,
    app_name: str,
    process_name: str,
    delay_seconds: float,
) -> str:
    recipient_q = quote_for_applescript(recipient)
    message_q = quote_for_applescript(message)
    app_name_q = quote_for_applescript(app_name)
    process_name_q = quote_for_applescript(process_name)
    delay = max(delay_seconds, 0.1)

    file_block = ""
    if send_file:
        file_block = f"""
        set the clipboard to (POSIX file {quote_for_applescript(str(report_path))})
        delay {delay}
        keystroke "v" using command down
        delay {delay}
        key code 36
        delay {delay}
"""

    return f"""
tell application {app_name_q} to activate
delay {delay}
tell application "System Events"
    tell process {process_name_q}
        set frontmost to true
        delay {delay}
        keystroke "f" using command down
        delay {delay}
        set the clipboard to {recipient_q}
        keystroke "v" using command down
        delay {delay}
        key code 36
        delay {delay}
        set the clipboard to {message_q}
        keystroke "v" using command down
        delay {delay}
        key code 36
        delay {delay}
{file_block}
    end tell
end tell
"""


def send_to_wechat(
    recipient: str,
    report_path: Path,
    message_template: str,
    send_file: bool,
    app_name: str,
    process_name: str,
    delay_seconds: float,
) -> None:
    if not recipient:
        raise ValueError("wechat_recipient is required")
    if send_file and not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    message = render_message(message_template, report_path)
    script = build_send_script(
        recipient=recipient,
        message=message,
        report_path=report_path,
        send_file=send_file,
        app_name=app_name,
        process_name=process_name,
        delay_seconds=delay_seconds,
    )

    logging.info("Sending report to WeChat recipient: %s", recipient)
    logging.info("Report path: %s", report_path)
    run_osascript(script)
    logging.info("WeChat send automation finished")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a configured report to WeChat.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help=f"Path to config JSON. Default: {DEFAULT_CONFIG}",
    )
    parser.add_argument("--recipient", help="Override config wechat_recipient.")
    parser.add_argument("--report", help="Override config report_path.")
    parser.add_argument("--message", help="Override config message_template.")
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="Send the text message only, without attaching the report file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser()

    try:
        config = load_config(config_path)
        setup_logging(config)

        report_path = Path(args.report or config.get("report_path", "")).expanduser()
        if not report_path.is_absolute():
            report_path = PROJECT_ROOT / report_path

        send_to_wechat(
            recipient=args.recipient or config.get("wechat_recipient", ""),
            report_path=report_path,
            message_template=args.message or config.get("message_template", "今日报告：$report_name"),
            send_file=not args.no_file and bool(config.get("send_file", True)),
            app_name=str(config.get("wechat_app_name", "WeChat")),
            process_name=str(config.get("wechat_process_name", config.get("wechat_app_name", "WeChat"))),
            delay_seconds=float(config.get("ui_delay_seconds", 0.7)),
        )
        return 0
    except Exception:
        logging.exception("Failed to send report to WeChat")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
