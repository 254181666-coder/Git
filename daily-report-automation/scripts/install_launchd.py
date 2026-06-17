#!/usr/bin/env python3
"""Install the daily report automation LaunchAgent for the current macOS user."""

from __future__ import annotations

import argparse
import json
import plistlib
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "daily_auto_send.json"
LABEL = "com.daily-report-automation"


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_send_time(send_time: str) -> tuple[int, int]:
    hour_text, minute_text = send_time.split(":", maxsplit=1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("send_time must be a valid HH:MM value")
    return hour, minute


def build_plist(config: dict, config_path: Path) -> dict:
    hour, minute = parse_send_time(str(config.get("send_time", "09:30")))
    logs_dir = PROJECT_ROOT / str(config.get("log_dir", "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    return {
        "Label": LABEL,
        "ProgramArguments": [
            "/usr/bin/python3",
            str(PROJECT_ROOT / "scripts" / "daily_auto_send.py"),
            "--config",
            str(config_path),
        ],
        "WorkingDirectory": str(PROJECT_ROOT),
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "StandardOutPath": str(logs_dir / "launchd.out.log"),
        "StandardErrorPath": str(logs_dir / "launchd.err.log"),
        "RunAtLoad": False,
    }


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, text=True, check=check)


def install(config_path: Path) -> Path:
    config = load_config(config_path)
    plist = build_plist(config, config_path)

    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / f"{LABEL}.plist"

    with plist_path.open("wb") as file:
        plistlib.dump(plist, file, sort_keys=False)

    run(["launchctl", "unload", str(plist_path)], check=False)
    run(["launchctl", "load", str(plist_path)])
    return plist_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the daily report LaunchAgent.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help=f"Path to config JSON. Default: {DEFAULT_CONFIG}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    plist_path = install(config_path)
    print(f"Installed LaunchAgent: {plist_path}")
    print(f"Check status with: launchctl print gui/$(id -u)/{LABEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
