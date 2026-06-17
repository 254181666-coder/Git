#!/usr/bin/env python3
"""Calculate BU03 AT+SETDEV calibration parameters from distance CSV files."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CalibrationPoint:
    actual_m: float
    reported_m: float
    count: int = 1


@dataclass(frozen=True)
class CalibrationResult:
    para_a: float
    para_b_m: float
    mae_before_m: float
    mae_after_m: float
    max_error_after_m: float
    r2: float
    points: tuple[CalibrationPoint, ...]

    @property
    def para_b_mm(self) -> float:
        return self.para_b_m * 1000.0


def load_points(paths: list[Path]) -> list[CalibrationPoint]:
    points: list[CalibrationPoint] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                actual = row.get("actual_distance", "").strip()
                reported = row.get("reported_distance", "").strip()
                if not actual or not reported:
                    continue
                points.append(CalibrationPoint(actual_m=float(actual), reported_m=float(reported)))
    return points


def group_points(points: list[CalibrationPoint]) -> list[CalibrationPoint]:
    buckets: dict[float, list[float]] = defaultdict(list)
    for point in points:
        buckets[point.actual_m].append(point.reported_m)

    grouped = []
    for actual_m, reported_values in sorted(buckets.items()):
        grouped.append(
            CalibrationPoint(
                actual_m=actual_m,
                reported_m=sum(reported_values) / len(reported_values),
                count=len(reported_values),
            )
        )
    return grouped


def fit_calibration(points: list[CalibrationPoint]) -> CalibrationResult:
    if len(points) < 2:
        raise ValueError("Need at least two distinct actual distances for linear calibration.")

    xs = [point.reported_m for point in points]
    ys = [point.actual_m for point in points]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if math.isclose(denominator, 0.0):
        raise ValueError("Reported distances are identical; cannot fit calibration.")

    para_a = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
    para_b_m = y_mean - para_a * x_mean

    before_errors = [abs(point.reported_m - point.actual_m) for point in points]
    after_values = [para_a * point.reported_m + para_b_m for point in points]
    after_errors = [abs(after - point.actual_m) for point, after in zip(points, after_values)]
    residual_sum = sum((point.actual_m - after) ** 2 for point, after in zip(points, after_values))
    total_sum = sum((point.actual_m - y_mean) ** 2 for point in points)
    r2 = 1.0 if math.isclose(total_sum, 0.0) else 1.0 - residual_sum / total_sum

    return CalibrationResult(
        para_a=para_a,
        para_b_m=para_b_m,
        mae_before_m=sum(before_errors) / len(before_errors),
        mae_after_m=sum(after_errors) / len(after_errors),
        max_error_after_m=max(after_errors),
        r2=r2,
        points=tuple(points),
    )


def build_setdev_command(
    result: CalibrationResult,
    cap: int,
    anndelay: int,
    kalman_enable: int,
    kalman_q: float,
    kalman_r: float,
    pos_enable: int,
    pos_dimen: int,
) -> str:
    return (
        f"AT+SETDEV={cap},{anndelay},{kalman_enable},"
        f"{kalman_q:.3f},{kalman_r:.3f},"
        f"{result.para_a:.4f},{result.para_b_mm:.2f},"
        f"{pos_enable},{pos_dimen}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fit BU03 distance calibration and print AT+SETDEV.")
    parser.add_argument("csv", nargs="+", type=Path, help="Distance CSV files from collector/bu03_collector.py.")
    parser.add_argument("--no-group", action="store_true", help="Fit every row directly instead of grouping by actual_distance.")
    parser.add_argument("--cap", type=int, default=10, help="AT+SETDEV tag capacity. Default: 10.")
    parser.add_argument("--anndelay", type=int, default=16336, help="AT+SETDEV antenna delay. Default: 16336.")
    parser.add_argument("--kalman-enable", type=int, default=1, help="AT+SETDEV Kalman enable. Default: 1.")
    parser.add_argument("--kalman-q", type=float, default=0.018, help="AT+SETDEV Kalman Q. Default: 0.018.")
    parser.add_argument("--kalman-r", type=float, default=0.642, help="AT+SETDEV Kalman R. Default: 0.642.")
    parser.add_argument("--pos-enable", type=int, default=0, help="AT+SETDEV positioning enable. Default: 0.")
    parser.add_argument("--pos-dimen", type=int, default=0, help="AT+SETDEV positioning dimension. Default: 0.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    raw_points = load_points(args.csv)
    points = raw_points if args.no_group else group_points(raw_points)
    result = fit_calibration(points)
    command = build_setdev_command(
        result,
        cap=args.cap,
        anndelay=args.anndelay,
        kalman_enable=args.kalman_enable,
        kalman_q=args.kalman_q,
        kalman_r=args.kalman_r,
        pos_enable=args.pos_enable,
        pos_dimen=args.pos_dimen,
    )

    print(f"raw_rows: {len(raw_points)}")
    print(f"fit_points: {len(points)}")
    print(f"para_a: {result.para_a:.6f}")
    print(f"para_b_m: {result.para_b_m:.6f}")
    print(f"para_b_mm: {result.para_b_mm:.2f}")
    print(f"mae_before_m: {result.mae_before_m:.4f}")
    print(f"mae_after_m: {result.mae_after_m:.4f}")
    print(f"max_error_after_m: {result.max_error_after_m:.4f}")
    print(f"r2: {result.r2:.4f}")
    print(f"command: {command}")
    print("save: AT+SAVE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
