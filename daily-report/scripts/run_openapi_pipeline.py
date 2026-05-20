#!/usr/bin/env python3
"""
运行 OpenAPI 数据管道：raw 同步 -> mart 物化 -> 质量检查。
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def default_target_date() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def run_step(name: str, cmd: list[str], keep_going: bool = False) -> bool:
    print("\n" + "=" * 60, flush=True)
    print(name, flush=True)
    print("=" * 60, flush=True)
    print("执行:", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print(f"✓ {name} 完成", flush=True)
        return True
    print(f"✗ {name} 失败，退出码: {result.returncode}", flush=True)
    if not keep_going:
        raise SystemExit(result.returncode)
    return False


def benchmark_files_exist(target_date: str) -> bool:
    base = PROJECT_ROOT / "data" / "benchmarks"
    return all(
        (base / f"{target_date}_{name}.csv").exists()
        for name in ("income_benchmark", "product_store_benchmark", "product_category_benchmark")
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="运行 OpenAPI raw -> mart 数据管道")
    parser.add_argument("target_date", nargs="?", default=default_target_date(), help="营业日期 YYYY-MM-DD，默认昨天")
    parser.add_argument("--skip-raw", action="store_true", help="跳过接口同步，只基于已有 raw 表重新物化")
    parser.add_argument("--skip-quality", action="store_true", help="跳过质量检查")
    parser.add_argument("--compare-benchmark", action="store_true", help="如果存在 benchmark CSV，则输出对账表")
    parser.add_argument("--keep-going", action="store_true", help="步骤失败后继续执行后续步骤")
    parser.add_argument("--shop-id", type=int, help="只同步单个 shop_id")
    parser.add_argument("--member-pages", type=int, default=1, help="会员列表同步页数")
    parser.add_argument("--consume-limit", type=int, default=50, help="消费画像同步数量上限")
    parser.add_argument("--page-size", type=int, default=100, help="接口分页大小")
    parser.add_argument("--timeout", type=int, default=90, help="接口超时时间秒")
    parser.add_argument("--active-mobiles", action="store_true", help="按当天团购/预订手机号同步消费画像")
    parser.add_argument("--sync-parent-details", action="store_true", help="同步当天相关开台单详情")
    parser.add_argument("--parent-detail-limit", type=int, default=0, help="开台单详情同步数量上限，0 不限制")
    parser.add_argument("--consume-only-missing", action="store_true", help="只同步尚未落库的消费画像/开台详情")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    python = sys.executable
    target_date = args.target_date
    success = True

    if not args.skip_raw:
        raw_cmd = [
            python,
            "scripts/sync_fun360_openapi_raw.py",
            target_date,
            "--member-pages",
            str(args.member_pages),
            "--consume-limit",
            str(args.consume_limit),
            "--page-size",
            str(args.page_size),
            "--timeout",
            str(args.timeout),
        ]
        if args.shop_id:
            raw_cmd.extend(["--shop-id", str(args.shop_id)])
        if args.active_mobiles:
            raw_cmd.append("--consume-active-mobiles")
        if args.sync_parent_details:
            raw_cmd.append("--sync-parent-details")
            raw_cmd.extend(["--parent-detail-limit", str(args.parent_detail_limit)])
        if args.consume_only_missing:
            raw_cmd.append("--consume-only-missing")
        success = run_step("1. 同步 OpenAPI raw 数据", raw_cmd, keep_going=args.keep_going) and success
    else:
        print("跳过 raw 同步", flush=True)

    success = run_step(
        "2. 物化 OpenAPI mart 汇总",
        [python, "scripts/materialize_openapi_daily_metrics.py", target_date],
        keep_going=args.keep_going,
    ) and success

    if not args.skip_quality:
        success = run_step(
            "3. 检查 OpenAPI 数据管道",
            [python, "scripts/check_openapi_pipeline.py", target_date],
            keep_going=args.keep_going,
        ) and success

    if args.compare_benchmark:
        if benchmark_files_exist(target_date):
            success = run_step(
                "4. 与业务基准对账",
                [python, "scripts/compare_openapi_to_benchmark.py", target_date],
                keep_going=args.keep_going,
            ) and success
        else:
            print(f"\n未找到 {target_date} 的 benchmark CSV，跳过对账。", flush=True)

    print("\n" + "=" * 60, flush=True)
    print(f"OpenAPI 数据管道完成: {'成功' if success else '存在失败步骤'}", flush=True)
    print("=" * 60, flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
