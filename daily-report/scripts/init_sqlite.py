#!/usr/bin/env python3
"""
初始化本地SQLite数据库。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DB_PATH
from src.database import get_connection


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT NOT NULL UNIQUE,
    fun360_shop_id INTEGER UNIQUE,
    image TEXT,
    images TEXT,
    address TEXT,
    lng TEXT,
    lat TEXT,
    opening_phone TEXT,
    opening_hours TEXT,
    province INTEGER,
    city INTEGER,
    district INTEGER,
    is_online INTEGER,
    tags TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS store_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    weekday TEXT,
    total_revenue REAL DEFAULT 0,
    actual_amount REAL DEFAULT 0,
    supermarket_revenue REAL DEFAULT 0,
    room_revenue REAL DEFAULT 0,
    stored_card_sales REAL DEFAULT 0,
    times_card_sales REAL DEFAULT 0,
    other_revenue REAL DEFAULT 0,
    transfer_fund REAL DEFAULT 0,
    online_groupbuy REAL DEFAULT 0,
    daily_batch_consumption REAL DEFAULT 0,
    customers_before_18 INTEGER DEFAULT 0,
    maintenance_before_18 INTEGER DEFAULT 0,
    customers_18_to_24 INTEGER DEFAULT 0,
    maintenance_18_to_24 INTEGER DEFAULT 0,
    customers_after_00 INTEGER DEFAULT 0,
    maintenance_after_00 INTEGER DEFAULT 0,
    peak_room_count INTEGER DEFAULT 0,
    peak_time TEXT,
    revenue REAL DEFAULT 0,
    customers INTEGER DEFAULT 0,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, data_date),
    FOREIGN KEY(store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS stored_value (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    member_level TEXT,
    stored_amount REAL DEFAULT 0,
    stored_count INTEGER DEFAULT 1,
    recharge_source TEXT,
    is_first_recharge INTEGER DEFAULT 0,
    marketing_manager TEXT,
    member_name TEXT,
    member_phone TEXT,
    room_principal REAL DEFAULT 0,
    room_gift REAL DEFAULT 0,
    drink_principal REAL DEFAULT 0,
    drink_gift REAL DEFAULT 0,
    payment_method TEXT,
    payment_amount REAL DEFAULT 0,
    points_change INTEGER DEFAULT 0,
    points_balance INTEGER DEFAULT 0,
    growth_change INTEGER DEFAULT 0,
    growth_balance INTEGER DEFAULT 0,
    total_balance REAL DEFAULT 0,
    principal_balance REAL DEFAULT 0,
    gift_balance REAL DEFAULT 0,
    recharge_time TEXT,
    external_id TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS product_sales_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    product_name TEXT,
    product_code TEXT,
    category TEXT,
    system_category TEXT,
    unit TEXT,
    unit_price REAL DEFAULT 0,
    quantity INTEGER DEFAULT 0,
    sales_amount REAL DEFAULT 0,
    big_category TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS product_sales_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    product_name TEXT,
    product_code TEXT,
    package TEXT,
    room_no TEXT,
    room_type TEXT,
    quantity INTEGER DEFAULT 0,
    sales_amount REAL DEFAULT 0,
    order_type TEXT,
    order_no TEXT,
    open_time TEXT,
    source_channel TEXT,
    actual_amount REAL DEFAULT 0,
    should_amount REAL DEFAULT 0,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS raw_openapi_members (
    member_id INTEGER PRIMARY KEY,
    mobile TEXT,
    username TEXT,
    register_shop_id INTEGER,
    register_at TEXT,
    status INTEGER,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_openapi_member_consume (
    member_id INTEGER PRIMARY KEY,
    mobile TEXT,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_openapi_mobile_consume (
    mobile TEXT PRIMARY KEY,
    member_id INTEGER,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_openapi_marketing_orders (
    order_id INTEGER PRIMARY KEY,
    shop_id INTEGER,
    mobile TEXT,
    biz_day TEXT,
    status INTEGER,
    pay_status INTEGER,
    paid_amount REAL DEFAULT 0,
    refund_amount REAL DEFAULT 0,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_openapi_preorders (
    preorder_id INTEGER,
    order_id TEXT,
    parent_order_id INTEGER,
    shop_name TEXT,
    preorder_mobile TEXT,
    arrival_time TEXT,
    status INTEGER,
    preorder_status INTEGER,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(preorder_id, order_id)
);

CREATE TABLE IF NOT EXISTS raw_openapi_parent_order_details (
    parent_order_id INTEGER PRIMARY KEY,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_openapi_products (
    product_id INTEGER,
    shop_id INTEGER,
    category_id INTEGER,
    category_name TEXT,
    product_name TEXT,
    sale_price REAL DEFAULT 0,
    status INTEGER,
    raw_json TEXT,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(product_id, shop_id)
);

CREATE TABLE IF NOT EXISTS openapi_daily_store_metrics (
    store_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    marketing_orders INTEGER DEFAULT 0,
    marketing_amount REAL DEFAULT 0,
    room_orders INTEGER DEFAULT 0,
    room_amount REAL DEFAULT 0,
    product_orders INTEGER DEFAULT 0,
    product_amount REAL DEFAULT 0,
    product_items INTEGER DEFAULT 0,
    stored_orders INTEGER DEFAULT 0,
    stored_amount REAL DEFAULT 0,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(store_id, data_date)
);

CREATE TABLE IF NOT EXISTS openapi_product_sales_items (
    store_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    data_date TEXT NOT NULL,
    product_name TEXT,
    category_id INTEGER,
    category TEXT,
    big_category TEXT,
    quantity INTEGER DEFAULT 0,
    sales_amount REAL DEFAULT 0,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(store_id, data_date, product_name, category_id)
);

CREATE INDEX IF NOT EXISTS idx_store_daily_date ON store_daily(data_date);
CREATE INDEX IF NOT EXISTS idx_stored_value_date ON stored_value(data_date);
CREATE INDEX IF NOT EXISTS idx_product_sales_summary_date ON product_sales_summary(data_date);
CREATE INDEX IF NOT EXISTS idx_product_sales_detail_date ON product_sales_detail(data_date);
CREATE INDEX IF NOT EXISTS idx_raw_openapi_members_mobile ON raw_openapi_members(mobile);
CREATE INDEX IF NOT EXISTS idx_raw_openapi_mobile_consume_member ON raw_openapi_mobile_consume(member_id);
CREATE INDEX IF NOT EXISTS idx_raw_openapi_marketing_orders_biz_day ON raw_openapi_marketing_orders(biz_day);
CREATE INDEX IF NOT EXISTS idx_raw_openapi_preorders_mobile ON raw_openapi_preorders(preorder_mobile);
CREATE INDEX IF NOT EXISTS idx_raw_openapi_products_shop ON raw_openapi_products(shop_id);
CREATE INDEX IF NOT EXISTS idx_openapi_daily_store_metrics_date ON openapi_daily_store_metrics(data_date);
CREATE INDEX IF NOT EXISTS idx_openapi_product_sales_items_date ON openapi_product_sales_items(data_date);
"""


MIGRATIONS = [
    ("raw_openapi_marketing_orders", "mobile", "ALTER TABLE raw_openapi_marketing_orders ADD COLUMN mobile TEXT"),
    ("openapi_product_sales_items", "big_category", "ALTER TABLE openapi_product_sales_items ADD COLUMN big_category TEXT"),
]


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        for table, column, sql in MIGRATIONS:
            columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if column not in columns:
                conn.execute(sql)
        conn.commit()
    finally:
        conn.close()
    print(f"SQLite数据库已初始化: {DB_PATH}")


if __name__ == "__main__":
    main()
