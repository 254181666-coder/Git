#!/usr/bin/env python3
"""
检查 OpenAPI raw -> mart 数据管道结果。
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection


RAW_CHECKS = (
    ("门店档案", "SELECT COUNT(*) FROM stores WHERE fun360_shop_id IS NOT NULL"),
    ("商品档案 raw", "SELECT COUNT(*) FROM raw_openapi_products"),
    ("团购/卡券订单 raw", "SELECT COUNT(*) FROM raw_openapi_marketing_orders WHERE biz_day = ?"),
    (
        "预订单 raw",
        "SELECT COUNT(*) FROM raw_openapi_preorders WHERE substr(arrival_time, 1, 10) IN (?, date(?, '+1 day'))",
    ),
)

MART_CHECKS = (
    ("支付事件 clean", "SELECT COUNT(*) FROM clean_payment_event WHERE business_date = ?"),
    ("商品明细 clean", "SELECT COUNT(*) FROM clean_order_item WHERE business_date = ?"),
    ("门店营收 mart", "SELECT COUNT(*) FROM mart_daily_store_revenue WHERE business_date = ?"),
    ("门店日指标 mart", "SELECT COUNT(*) FROM openapi_daily_store_metrics WHERE data_date = ?"),
    ("商品销售 mart", "SELECT COUNT(*) FROM openapi_product_sales_items WHERE data_date = ?"),
)


def count_for(conn, sql: str, target_date: str) -> int:
    params = (target_date, target_date) if sql.count("?") == 2 else (target_date,) if "?" in sql else ()
    return int(conn.execute(sql, params).fetchone()[0] or 0)


def print_row(ok: bool, label: str, detail: str) -> None:
    icon = "✓" if ok else "✗"
    print(f"  {icon} {label}: {detail}")


def run_checks(target_date: str, strict: bool = False) -> int:
    failures = 0
    conn = get_connection()
    try:
        print("=" * 60)
        print(f"OpenAPI 数据管道检查 / 数据日期: {target_date}")
        print("=" * 60)

        print("\nRaw 层")
        for label, sql in RAW_CHECKS:
            count = count_for(conn, sql, target_date)
            ok = count > 0
            print_row(ok, label, f"{count} 行")
            if strict and not ok:
                failures += 1

        print("\nMart 层")
        for label, sql in MART_CHECKS:
            count = count_for(conn, sql, target_date)
            ok = count > 0
            print_row(ok, label, f"{count} 行")
            if not ok:
                failures += 1

        print("\n质量规则")
        orphan_metrics = count_for(
            conn,
            """
            SELECT COUNT(*)
            FROM openapi_daily_store_metrics m
            LEFT JOIN stores s ON m.store_id = s.id
            WHERE m.data_date = ? AND s.id IS NULL
            """,
            target_date,
        )
        print_row(orphan_metrics == 0, "mart 门店引用完整", f"{orphan_metrics} 条孤儿记录")
        failures += 1 if orphan_metrics else 0

        uncategorized = count_for(
            conn,
            """
            SELECT COUNT(*)
            FROM openapi_product_sales_items
            WHERE data_date = ? AND (big_category IS NULL OR big_category = '')
            """,
            target_date,
        )
        print_row(uncategorized == 0, "商品大类已归一", f"{uncategorized} 条未归类")
        failures += 1 if uncategorized else 0

        negative_quantity = count_for(
            conn,
            """
            SELECT COUNT(*)
            FROM openapi_product_sales_items
            WHERE data_date = ? AND quantity < 0
            """,
            target_date,
        )
        print_row(negative_quantity == 0, "商品数量非负", f"{negative_quantity} 条异常")
        failures += 1 if negative_quantity else 0

        negative_amount = count_for(
            conn,
            """
            SELECT COUNT(*)
            FROM openapi_product_sales_items
            WHERE data_date = ? AND sales_amount < 0
            """,
            target_date,
        )
        if negative_amount:
            print(f"  ! 商品净销售额为负: {negative_amount} 条，通常来自退款/冲减，保留用于对账")
        else:
            print_row(True, "商品净销售额检查", "无负金额")

        totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(marketing_amount), 0) AS marketing_amount,
                COALESCE(SUM(stored_amount), 0) AS stored_amount,
                COALESCE(SUM(room_amount), 0) AS room_amount,
                COALESCE(SUM(product_amount), 0) AS product_amount
            FROM openapi_daily_store_metrics
            WHERE data_date = ?
            """,
            (target_date,),
        ).fetchone()
        print("\n汇总金额")
        print(f"  团购: {float(totals['marketing_amount'] or 0):,.2f}")
        print(f"  储值: {float(totals['stored_amount'] or 0):,.2f}")
        print(f"  房费: {float(totals['room_amount'] or 0):,.2f}")
        print(f"  商品: {float(totals['product_amount'] or 0):,.2f}")

        clean_mart_diff = conn.execute(
            """
            SELECT
                (
                    SELECT COALESCE(SUM(amount), 0)
                    FROM clean_payment_event
                    WHERE business_date = ? AND is_revenue_recognized = 1
                ) - (
                    SELECT COALESCE(SUM(total_revenue), 0)
                    FROM mart_daily_store_revenue
                    WHERE business_date = ?
                ) AS diff
            """,
            (target_date, target_date),
        ).fetchone()["diff"]
        diff_abs = abs(float(clean_mart_diff or 0))
        print_row(diff_abs < 0.005, "clean 到 mart 收入闭合", f"差异 {diff_abs:,.2f}")
        failures += 1 if diff_abs >= 0.005 else 0

        mart_totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(marketing_amount), 0) AS marketing_amount,
                COALESCE(SUM(stored_amount), 0) AS stored_amount,
                COALESCE(SUM(room_amount), 0) AS room_amount,
                COALESCE(SUM(product_amount), 0) AS product_amount,
                COALESCE(SUM(total_revenue), 0) AS total_revenue
            FROM mart_daily_store_revenue
            WHERE business_date = ?
            """,
            (target_date,),
        ).fetchone()
        print("\n正式 Mart 营收")
        print(f"  总营收: {float(mart_totals['total_revenue'] or 0):,.2f}")
        print(f"  团购: {float(mart_totals['marketing_amount'] or 0):,.2f}")
        print(f"  储值: {float(mart_totals['stored_amount'] or 0):,.2f}")
        print(f"  房费: {float(mart_totals['room_amount'] or 0):,.2f}")
        print(f"  商品: {float(mart_totals['product_amount'] or 0):,.2f}")
    finally:
        conn.close()

    print("\n" + "=" * 60)
    if failures:
        print(f"检查未通过: {failures} 项")
        return 1
    print("检查通过")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="检查 OpenAPI 数据管道结果")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    parser.add_argument("--strict-raw", action="store_true", help="raw 层缺数据时也返回失败")
    args = parser.parse_args(argv)
    return run_checks(args.target_date, strict=args.strict_raw)


if __name__ == "__main__":
    raise SystemExit(main())
