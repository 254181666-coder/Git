#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import date
import pymysql
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

print("获取上东店和晨宇店5月数据...\n")

# 获取这两个门店的ID
cursor.execute("SELECT id, store_name FROM stores WHERE store_name IN ('上东店', '晨宇店')")
stores = cursor.fetchall()
store_map = {s['store_name']: s['id'] for s in stores}
print(f"门店信息：{store_map}")

# 获取5月的日营业数据
cursor.execute("""
    SELECT 
        s.store_name,
        sd.data_date,
        sd.weekday,
        sd.total_revenue,
        sd.actual_amount,
        sd.supermarket_revenue,
        sd.room_revenue,
        sd.stored_card_sales,
        sd.customers
    FROM store_daily sd
    JOIN stores s ON sd.store_id = s.id
    WHERE s.store_name IN ('上东店', '晨宇店')
        AND sd.data_date >= '2026-05-01'
        AND sd.data_date < '2026-06-01'
    ORDER BY s.store_name, sd.data_date
""")
daily_data = cursor.fetchall()

df = pd.DataFrame(daily_data)
print(f"\n5月数据行数：{len(df)}")
print(f"\n数据预览：")
print(df.to_string(index=False))

# 按门店分组统计
print(f"\n\n=== 5月总览 ===")
for store in ['上东店', '晨宇店']:
    store_df = df[df['store_name'] == store]
    print(f"\n{store}:")
    print(f"  天数: {len(store_df)}")
    print(f"  总营业额: {store_df['total_revenue'].sum():,.2f}")
    print(f"  日均营业额: {store_df['total_revenue'].mean():,.2f}")
    print(f"  最高日: {store_df['total_revenue'].max():,.2f} ({store_df.loc[store_df['total_revenue'].idxmax(), 'data_date']})")
    print(f"  最低日: {store_df['total_revenue'].min():,.2f} ({store_df.loc[store_df['total_revenue'].idxmin(), 'data_date']})")
    print(f"  超市总收入: {store_df['supermarket_revenue'].sum():,.2f}")
    print(f"  房费总收入: {store_df['room_revenue'].sum():,.2f}")
    print(f"  储值卡总销售: {store_df['stored_card_sales'].sum():,.2f}")
    print(f"  总待客台数: {store_df['customers'].sum()}")

cursor.close()
conn.close()

# 保存数据以便后续使用
df.to_csv(PROJECT_ROOT / "reports" / "may_stores_data.csv", index=False)
print(f"\n\n数据已保存到: reports/may_stores_data.csv")
