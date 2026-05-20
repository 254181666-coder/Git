#!/usr/bin/env python3
"""
对比 OpenAPI 物化结果与业务基准日报。
"""
import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection


def money(value):
    return float(value or 0)


def load_csv(path):
    with open(path, "r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def short_store_name(name):
    rules = {
        "上东": "上东",
        "松原一": "松原一",
        "通辽": "通辽",
        "佳木斯": "佳木斯",
        "晨宇": "晨宇",
        "通化": "通化",
        "鸡西": "鸡西",
        "红旗街": "红旗街",
        "榆树": "榆树",
        "安达": "安达",
        "法库": "法库",
        "松原二": "松原二",
    }
    for keyword, store in rules.items():
        if keyword in (name or ""):
            return store
    return name


def openapi_income(conn, target_date):
    rows = conn.execute(
        """
        SELECT s.store_name, m.marketing_amount, m.stored_amount,
               m.room_amount + m.product_amount AS other_income,
               m.marketing_amount + m.stored_amount + m.room_amount + m.product_amount AS total_revenue
        FROM openapi_daily_store_metrics m
        JOIN stores s ON m.store_id = s.id
        WHERE m.data_date = ?
        """,
        (target_date,),
    ).fetchall()
    return {
        short_store_name(row["store_name"]): {
            "online_groupbuy": money(row["marketing_amount"]),
            "stored_card_sales": money(row["stored_amount"]),
            "other_income": money(row["other_income"]),
            "total_revenue": money(row["total_revenue"]),
        }
        for row in rows
    }


def openapi_product_store(conn, target_date):
    rows = conn.execute(
        """
        SELECT s.store_name, SUM(i.sales_amount) AS sales_amount
        FROM openapi_product_sales_items i
        JOIN stores s ON i.store_id = s.id
        WHERE i.data_date = ?
        GROUP BY s.store_name
        """,
        (target_date,),
    ).fetchall()
    return {short_store_name(row["store_name"]): money(row["sales_amount"]) for row in rows}


def openapi_product_category(conn, target_date):
    rows = conn.execute(
        """
        SELECT big_category, COUNT(*) AS product_count,
               SUM(quantity) AS quantity, SUM(sales_amount) AS sales_amount
        FROM openapi_product_sales_items
        WHERE data_date = ?
        GROUP BY big_category
        """,
        (target_date,),
    ).fetchall()
    return {
        row["big_category"]: {
            "product_count": int(row["product_count"] or 0),
            "quantity": int(row["quantity"] or 0),
            "sales_amount": money(row["sales_amount"]),
        }
        for row in rows
    }


def print_table(title, headers, rows):
    print(f"\n{title}")
    print("\t".join(headers))
    for row in rows:
        print("\t".join(str(value) for value in row))


def main():
    parser = argparse.ArgumentParser(description="对比 OpenAPI 与业务基准日报")
    parser.add_argument("target_date", help="营业日期 YYYY-MM-DD")
    args = parser.parse_args()

    base = PROJECT_ROOT / "data" / "benchmarks"
    income_rows = load_csv(base / f"{args.target_date}_income_benchmark.csv")
    product_store_rows = load_csv(base / f"{args.target_date}_product_store_benchmark.csv")
    product_category_rows = load_csv(base / f"{args.target_date}_product_category_benchmark.csv")

    conn = get_connection()
    try:
        income = openapi_income(conn, args.target_date)
        product_store = openapi_product_store(conn, args.target_date)
        product_category = openapi_product_category(conn, args.target_date)
    finally:
        conn.close()

    print_table(
        "收入口径对账",
        ["门店", "基准总营收", "OpenAPI粗总额", "总差异", "基准储值", "OpenAPI储值", "基准团购", "OpenAPI团购"],
        [
            [
                row["store"],
                f"{money(row['total_revenue']):.0f}",
                f"{income.get(row['store'], {}).get('total_revenue', 0):.0f}",
                f"{income.get(row['store'], {}).get('total_revenue', 0) - money(row['total_revenue']):.0f}",
                f"{money(row['stored_card_sales']):.0f}",
                f"{income.get(row['store'], {}).get('stored_card_sales', 0):.0f}",
                f"{money(row['online_groupbuy']):.0f}",
                f"{income.get(row['store'], {}).get('online_groupbuy', 0):.0f}",
            ]
            for row in income_rows
        ],
    )

    print_table(
        "商品门店对账",
        ["门店", "基准商品额", "OpenAPI商品额", "差异"],
        [
            [
                row["store"],
                f"{money(row['total']):.2f}",
                f"{product_store.get(row['store'], 0):.2f}",
                f"{product_store.get(row['store'], 0) - money(row['total']):.2f}",
            ]
            for row in product_store_rows
        ],
    )

    print_table(
        "商品大类对账",
        ["大类", "基准金额", "OpenAPI金额", "金额差异", "基准数量", "OpenAPI数量"],
        [
            [
                row["category"],
                f"{money(row['sales_amount']):.2f}",
                f"{product_category.get(row['category'], {}).get('sales_amount', 0):.2f}",
                f"{product_category.get(row['category'], {}).get('sales_amount', 0) - money(row['sales_amount']):.2f}",
                row["quantity"],
                product_category.get(row["category"], {}).get("quantity", 0),
            ]
            for row in product_category_rows
        ],
    )


if __name__ == "__main__":
    main()
