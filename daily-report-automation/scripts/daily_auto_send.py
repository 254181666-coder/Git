#!/usr/bin/env python3
"""Entry point used by launchd for the first-stage daily report automation."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "daily_auto_send.json"
SEND_SCRIPT = PROJECT_ROOT / "scripts" / "send_to_wechat.py"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def setup_logging(config: dict) -> Path:
    log_dir = Path(config.get("log_dir", PROJECT_ROOT / "logs")).expanduser()
    if not log_dir.is_absolute():
        log_dir = PROJECT_ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "daily_auto_send.log"
    logging.basicConfig(
        level=getattr(logging, str(config.get("log_level", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def configured_time_matches(config: dict, now: datetime) -> bool:
    """Optional guard for manual runs; launchd should usually schedule exactly."""
    send_time = str(config.get("send_time", "")).strip()
    if not send_time:
        return True

    try:
        hour_text, minute_text = send_time.split(":", maxsplit=1)
        return now.hour == int(hour_text) and now.minute == int(minute_text)
    except ValueError:
        raise ValueError("send_time must use HH:MM format, for example 09:30")


def run_send(config_path: Path, no_file: bool) -> None:
    command = [sys.executable, str(SEND_SCRIPT), "--config", str(config_path)]
    if no_file:
        command.append("--no-file")
    logging.info("Running send command: %s", " ".join(command))
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily automation entry point.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help=f"Path to config JSON. Default: {DEFAULT_CONFIG}",
    )
    parser.add_argument(
        "--ignore-time",
        action="store_true",
        help="Send immediately even when current HH:MM differs from config send_time.",
    )
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

        now = datetime.now()
        logging.info("Daily auto-send started at %s", now.isoformat(timespec="seconds"))
        if not args.ignore_time and not configured_time_matches(config, now):
            logging.info("Current time does not match configured send_time; skipping")
            return 0

        run_send(config_path, args.no_file)
        logging.info("Daily auto-send finished")
        return 0
    except Exception:
        logging.exception("Daily auto-send failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
