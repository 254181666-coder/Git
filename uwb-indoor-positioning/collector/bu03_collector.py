#!/usr/bin/env python3
"""BU03-Kit serial collector.

The collector keeps every line from the serial port, then writes a normalized
distance row only when the line contains a recognizable range value.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


RAW_FIELDS = ["timestamp", "port", "baudrate", "line"]
DISTANCE_FIELDS = [
    "timestamp",
    "tag_id",
    "anchor_id",
    "actual_x",
    "actual_y",
    "actual_distance",
    "reported_distance",
    "line_of_sight",
    "notes",
]

DISTANCE_RE = re.compile(
    r"""
    (?P<label>
        \b(?:dist(?:ance)?|range|rng|ranging|d)\b
        \s*[:=]?\s*
    )?
    (?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))
    \s*
    (?P<unit>mm|millimeter(?:s)?|cm|centimeter(?:s)?|m|meter(?:s)?)?
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)
TAG_RE = re.compile(r"\b(?:tag|tag_id|tid)\s*[:=]\s*(?P<id>[A-Za-z0-9_-]+)\b", re.IGNORECASE)
ANCHOR_RE = re.compile(
    r"\b(?:anchor|anchor_id|aid)\s*[:=]\s*(?P<id>[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DistanceSample:
    reported_distance_m: float
    tag_id: str = ""
    anchor_id: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def parse_distance_line(
    line: str,
    default_tag_id: str = "",
    default_anchor_id: str = "",
) -> DistanceSample | None:
    """Parse common BU03/TWR style range lines into meters.

    Vendor output formats vary by firmware, so this accepts common labels like
    DIST/RANGE/RNG and units in mm, cm, or m. Unknown lines return None.
    """

    match = next(
        (candidate for candidate in DISTANCE_RE.finditer(line) if candidate.group("label") or candidate.group("unit")),
        None,
    )
    if not match:
        return None

    value = float(match.group("value"))
    unit = (match.group("unit") or "m").lower()
    if unit.startswith("mm") or unit.startswith("millimeter"):
        distance_m = value / 1000.0
    elif unit.startswith("cm") or unit.startswith("centimeter"):
        distance_m = value / 100.0
    else:
        distance_m = value

    tag_match = TAG_RE.search(line)
    anchor_match = ANCHOR_RE.search(line)
    return DistanceSample(
        reported_distance_m=distance_m,
        tag_id=tag_match.group("id") if tag_match else default_tag_id,
        anchor_id=anchor_match.group("id") if anchor_match else default_anchor_id,
    )


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_header_if_needed(path: Path, fields: Iterable[str]) -> None:
    ensure_parent(path)
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.DictWriter(handle, fieldnames=list(fields)).writeheader()


def append_row(path: Path, fields: list[str], row: dict[str, str]) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writerow(row)


def default_capture_path(kind: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("data") / "captures" / f"bu03-{kind}-{stamp}.csv"


def open_serial(port: str, baudrate: int, timeout: float):
    try:
        import serial
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pyserial. Install it with `python3 -m pip install -r collector/requirements.txt`."
        ) from exc

    return serial.Serial(port=port, baudrate=baudrate, timeout=timeout)


def collect(args: argparse.Namespace) -> int:
    raw_csv = Path(args.raw_csv)
    distance_csv = Path(args.distance_csv)
    write_header_if_needed(raw_csv, RAW_FIELDS)
    write_header_if_needed(distance_csv, DISTANCE_FIELDS)

    with open_serial(args.port, args.baudrate, args.timeout) as serial_port:
        next_command_at = 0.0

        def send_command() -> None:
            serial_port.write((args.command + args.command_suffix).encode(args.encoding))
            serial_port.flush()

        print(f"Collecting from {args.port} at {args.baudrate}. Press Ctrl+C to stop.", file=sys.stderr)
        while True:
            if args.command and time.monotonic() >= next_command_at:
                send_command()
                if args.repeat_command_interval > 0:
                    next_command_at = time.monotonic() + args.repeat_command_interval
                else:
                    next_command_at = float("inf")

            raw = serial_port.readline()
            if not raw:
                continue

            timestamp = now_iso()
            line = raw.decode(args.encoding, errors="replace").strip()
            append_row(
                raw_csv,
                RAW_FIELDS,
                {
                    "timestamp": timestamp,
                    "port": args.port,
                    "baudrate": str(args.baudrate),
                    "line": line,
                },
            )

            sample = parse_distance_line(line, args.tag_id, args.anchor_id)
            if sample:
                append_row(
                    distance_csv,
                    DISTANCE_FIELDS,
                    {
                        "timestamp": timestamp,
                        "tag_id": sample.tag_id,
                        "anchor_id": sample.anchor_id,
                        "actual_x": args.actual_x,
                        "actual_y": args.actual_y,
                        "actual_distance": args.actual_distance,
                        "reported_distance": f"{sample.reported_distance_m:.4f}",
                        "line_of_sight": args.line_of_sight,
                        "notes": args.notes,
                    },
                )

            if args.echo:
                print(line)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect BU03-Kit serial output into raw and distance CSV files.")
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/tty.usbserial-0001.")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate. Default: 115200.")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds.")
    parser.add_argument("--encoding", default="utf-8", help="Serial text encoding. Default: utf-8.")
    parser.add_argument("--echo", action="store_true", help="Print decoded serial lines while collecting.")
    parser.add_argument("--command", help="Optional command to send once after opening the port, such as AT.")
    parser.add_argument("--command-suffix", default="\r\n", help="Suffix for --command. Default: CRLF.")
    parser.add_argument(
        "--repeat-command-interval",
        type=float,
        default=0.0,
        help="Repeat --command every N seconds. Default: 0, send once.",
    )
    parser.add_argument("--raw-csv", default=str(default_capture_path("raw")), help="Raw line CSV path.")
    parser.add_argument("--distance-csv", default=str(default_capture_path("distance")), help="Normalized distance CSV path.")
    parser.add_argument("--tag-id", default="", help="Default tag id when the serial line does not include one.")
    parser.add_argument("--anchor-id", default="", help="Default anchor id when the serial line does not include one.")
    parser.add_argument("--actual-x", default="", help="Optional measured test point x coordinate.")
    parser.add_argument("--actual-y", default="", help="Optional measured test point y coordinate.")
    parser.add_argument("--actual-distance", default="", help="Optional tape-measured distance in meters.")
    parser.add_argument("--line-of-sight", default="", help="yes/no or notes about line of sight.")
    parser.add_argument("--notes", default="", help="Notes copied into each normalized distance row.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return collect(args)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
