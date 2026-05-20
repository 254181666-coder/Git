#!/usr/bin/env python3
"""
每日报告生成主脚本
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import shutil
import argparse
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DELIVERY_DIR, LOGS_DIR, OUTPUT_DIR
from src.database import query
from src.report_paths import daily_report_artifacts, daily_report_files
from scripts.health_check import run_health_check

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")
    log_file = LOGS_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def run_python_script(script_name, target_date, extra_args=None):
    extra_args = extra_args or []
    log(f"执行: {script_name} {target_date} {' '.join(extra_args)}".strip())
    script_path = PROJECT_ROOT / "scripts" / script_name
    if not script_path.exists():
        log(f"  ✗ 脚本不存在")
        return False
    result = subprocess.run(
        [sys.executable, str(script_path), target_date, *extra_args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    if result.returncode == 0:
        log(f"  ✓ 成功")
        return True
    else:
        log(f"  ✗ 失败")
        if result.stdout:
            log("  stdout:")
            for line in result.stdout.strip().splitlines()[-20:]:
                log(f"    {line}")
        if result.stderr:
            log("  stderr:")
            for line in result.stderr.strip().splitlines()[-20:]:
                log(f"    {line}")
        return False


def sync_data(target_date):
    log("[0/4] 同步 Fun360 数据...")
    return run_python_script("sync_fun360_daily_data.py", target_date)


def health_check(target_date):
    log("运行健康检查...")
    result = run_health_check(target_date)
    if result == 0:
        log("  ✓ 健康检查通过")
        return True
    log("  ✗ 健康检查未通过")
    return False


def data_ready(target_date):
    checks = [
        ("store_daily", "SELECT COUNT(*) AS cnt FROM store_daily WHERE data_date = %s"),
        ("product_sales_summary", "SELECT COUNT(*) AS cnt FROM product_sales_summary WHERE data_date = %s"),
    ]
    ready = True
    for name, sql in checks:
        try:
            df = query(sql, (target_date,))
            count = int(df.iloc[0]["cnt"]) if not df.empty else 0
        except Exception as exc:
            log(f"  ✗ 数据检查失败 {name}: {exc}")
            return False
        if count <= 0:
            log(f"  ✗ 缺少 {name} 数据: {target_date}")
            ready = False
        else:
            log(f"  ✓ {name}: {count} 行")
    return ready

def clear_extended_attributes(file_path: Path):
    """清除文件的扩展属性，避免访问权限问题"""
    import subprocess
    import os
    try:
        # 清除所有扩展属性
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
        # 确保文件权限正确
        os.chmod(str(file_path), 0o644)
        # 尝试清除隔离属性（针对macOS）
        try:
            subprocess.run(['xattr', '-d', 'com.apple.quarantine', str(file_path)], capture_output=True)
        except:
            pass
    except:
        pass


def copy_files_to_delivery(target_date):
    log("复制报告到交付目录...")
    for src in daily_report_files(target_date):
        if src.exists():
            dest = DELIVERY_DIR / src.name
            shutil.copy2(str(src), str(dest))
            clear_extended_attributes(dest)
            log(f"  ✓ {src.name}")
        else:
            log(f"  ⚠️ 文件不存在: {src.name}")


def validate_report_outputs(target_date):
    log("校验报告产物...")
    ok = True
    for artifact in daily_report_artifacts(target_date):
        path = artifact.path
        if not path.exists():
            level = "✗" if artifact.required else "⚠️"
            log(f"  {level} 缺少产物: {artifact.label} ({path.name})")
            ok = ok and not artifact.required
            continue
        size = path.stat().st_size
        if size < 1024:
            level = "✗" if artifact.required else "⚠️"
            log(f"  {level} 产物异常偏小: {artifact.label} ({path.name}, {size} bytes)")
            ok = ok and not artifact.required
            continue
        log(f"  ✓ {artifact.label}: {path.name} ({size / 1024:.1f} KB)")
    return ok

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="生成每日报告")
    parser.add_argument(
        "target_date",
        nargs="?",
        default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="数据日期，格式 YYYY-MM-DD，默认昨天",
    )
    parser.add_argument(
        "--sync",
        dest="sync",
        action="store_true",
        default=os.getenv("DAILY_REPORT_SYNC", "1") != "0",
        help="生成前先同步 Fun360 数据，默认开启",
    )
    parser.add_argument(
        "--no-sync",
        dest="sync",
        action="store_false",
        help="跳过 Fun360 数据同步，只使用本地数据库",
    )
    parser.add_argument(
        "--allow-missing-data",
        action="store_true",
        help="数据检查不通过时仍继续生成报告",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="跳过目录和数据库基础健康检查",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    target_date = args.target_date

    log("=" * 60)
    log(f"每日报告生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} / 数据日期: {target_date}")
    log("=" * 60)

    if args.sync and not sync_data(target_date):
        log("数据同步失败，停止生成。可用 --no-sync 跳过同步。")
        return 1

    if not args.skip_health_check and not health_check(target_date):
        log("健康检查失败，停止生成。可用 --skip-health-check 跳过基础检查。")
        return 1

    log("")
    log("检查本地数据...")
    if not data_ready(target_date):
        if not args.allow_missing_data:
            log("数据未就绪，停止生成。可用 --allow-missing-data 强制继续。")
            return 1
        log("数据未就绪，但按参数要求继续生成。")

    success = 0
    log("")
    log("[1/4] 生成轻舟日报图表...")
    if run_python_script("generate_qingzhou_charts.py", target_date):
        success += 1
    log("")
    log("[2/4] 生成商品销售报告...")
    if run_python_script("generate_product_sales_report.py", target_date):
        success += 1
    log("")
    log("[3/4] 生成同比对比报告...")
    if run_python_script("generate_yearly_comparison_report.py", target_date):
        success += 1
    log("")
    log("[4/4] 复制到交付目录...")
    copy_files_to_delivery(target_date)
    log("")
    outputs_ok = validate_report_outputs(target_date)
    log("")
    log("=" * 60)
    log(f"完成 ({success}/3 成功，产物校验: {'通过' if outputs_ok else '未通过'})")
    log("=" * 60)
    return 0 if success == 3 and outputs_ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
