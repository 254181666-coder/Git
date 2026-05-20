#!/usr/bin/env python3
"""
每日报告健康检查。

检查内容偏向日报运行前最容易出问题的基础条件：
- 关键目录可写
- SQLite 数据库存在且关键表结构完整
- 目标日期是否已有核心业务数据
"""
import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DB_PATH, DELIVERY_DIR, LOGS_DIR, OUTPUT_DIR

REQUIRED_TABLES = (
    "stores",
    "store_daily",
    "stored_value",
    "product_sales_summary",
)

DATA_CHECKS = (
    ("store_daily", "SELECT COUNT(*) FROM store_daily WHERE data_date = ?"),
    ("product_sales_summary", "SELECT COUNT(*) FROM product_sales_summary WHERE data_date = ?"),
)


def default_target_date() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def print_result(ok: bool, message: str) -> None:
    icon = "✓" if ok else "✗"
    print(f"  {icon} {message}")


def print_warning(message: str) -> None:
    print(f"  ! {message}")


def check_writable_dir(path: Path) -> bool:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path, prefix=".health_check_", delete=True):
            return True
    except OSError:
        return False


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def run_health_check(target_date: str, strict_data: bool = False) -> int:
    print("=" * 60)
    print(f"每日报告健康检查 / 数据日期: {target_date}")
    print("=" * 60)

    failures = 0

    print("\n目录检查")
    for label, path in (
        ("输出目录", OUTPUT_DIR),
        ("日志目录", LOGS_DIR),
        ("交付目录", DELIVERY_DIR),
    ):
        ok = check_writable_dir(path)
        print_result(ok, f"{label}可写: {path}")
        failures += 0 if ok else 1

    print("\n数据库检查")
    if not DB_PATH.exists():
        print_result(False, f"数据库不存在: {DB_PATH}")
        return 1

    try:
        conn = sqlite3.connect(DB_PATH)
        names = table_names(conn)
        missing_tables = [name for name in REQUIRED_TABLES if name not in names]
        if missing_tables:
            print_result(False, f"缺少数据表: {', '.join(missing_tables)}")
            failures += 1
        else:
            print_result(True, f"关键数据表完整: {len(REQUIRED_TABLES)} 个")

        print("\n数据检查")
        for name, sql in DATA_CHECKS:
            if name not in names:
                continue
            count = int(conn.execute(sql, (target_date,)).fetchone()[0])
            ok = count > 0
            if ok:
                print_result(True, f"{name}: {count} 行")
            elif strict_data:
                print_result(False, f"{name}: {count} 行")
                failures += 1
            else:
                print_warning(f"{name}: {count} 行，日报主流程会继续做严格数据检查")
    except sqlite3.Error as exc:
        print_result(False, f"数据库读取失败: {exc}")
        failures += 1
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass

    print("\n" + "=" * 60)
    if failures:
        print(f"健康检查未通过: {failures} 项")
        return 1
    print("健康检查通过")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="检查每日报告运行环境")
    parser.add_argument("target_date", nargs="?", default=default_target_date(), help="数据日期，格式 YYYY-MM-DD")
    parser.add_argument("--strict-data", action="store_true", help="目标日期缺少业务数据时返回失败")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return run_health_check(args.target_date, strict_data=args.strict_data)


if __name__ == "__main__":
    raise SystemExit(main())
