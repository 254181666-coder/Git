#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
import pymysql
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
desktop_path = Path.home() / "Desktop"
source_dir = PROJECT_ROOT / "data" / "source"

# 1. 复制文件
print("1. 复制文件...")
source_file = desktop_path / "日营业数据表_21109.xlsx"
target_file = source_dir / "日营业数据表_21109.xlsx"

shutil.copy(source_file, target_file)
print(f"✓ 文件已复制到: {target_file}")

# 2. 读取文件并导入数据库
print("\n2. 读取文件并导入数据库...")
df = pd.read_excel(target_file)

conn = pymysql.connect(
    host="localhost",
    port=3306,
    user="root",
    password="CHANGE_ME_MYSQL_PASSWORD",
    database="ktv_analysis",
    charset="utf8mb4"
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 3. 先删除2026年5月已有的数据
print("3. 删除2026年5月已有的数据...")
delete_sql = """
DELETE FROM store_daily 
WHERE data_date BETWEEN '2026-05-01' AND '2026-05-13'
"""
cursor.execute(delete_sql)
conn.commit()
print(f"✓ 已删除 {cursor.rowcount} 条数据")

# 4. 导入新数据
print("4. 导入新数据...")
from utils import simplify_store_name
from config import STORE_PREFIXES, EXCLUDE_STORES, NAME_MAP

count = 0
for _, row in df.iterrows():
    store_name = simplify_store_name(str(row['门店']))
    if not store_name:
        continue
    
    # 获取或创建门店ID
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
    store_result = cursor.fetchone()
    if store_result:
        store_id = store_result['id']
    else:
        cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
        store_id = cursor.lastrowid
    
    # 插入数据
    insert_sql = """
    INSERT INTO store_daily (
        store_id, data_date, weekday, total_revenue, actual_amount,
        supermarket_revenue, room_revenue, stored_card_sales,
        times_card_sales, other_revenue, transfer_fund, online_groupbuy,
        daily_batch_consumption, customers_before_18, maintenance_before_18,
        customers_18_to_24, maintenance_18_to_24,
        customers_after_00, maintenance_after_00,
        peak_room_count, peak_time,
        customers, revenue
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    values = [
        store_id, str(row['日期']), str(row['星期']),
        float(row['总计营业额']) if pd.notna(row['总计营业额']) else 0,
        float(row['实收金额']) if pd.notna(row['实收金额']) else 0,
        float(row['超市收入']) if pd.notna(row['超市收入']) else 0,
        float(row['房费收入']) if pd.notna(row['房费收入']) else 0,
        float(row['储值卡销售']) if pd.notna(row['储值卡销售']) else 0,
        float(row['次卡销售']) if pd.notna(row['次卡销售']) else 0,
        float(row['营业外']) if pd.notna(row['营业外']) else 0,
        float(row['往来资金']) if pd.notna(row['往来资金']) else 0,
        float(row['线上团购应收']) if pd.notna(row['线上团购应收']) else 0,
        float(row['日单批消费']) if pd.notna(row['日单批消费']) else 0,
        int(row['18点前待客']) if pd.notna(row['18点前待客']) else 0,
        int(row['18点前维护']) if pd.notna(row['18点前维护']) else 0,
        int(row['18点-24点待客']) if pd.notna(row['18点-24点待客']) else 0,
        int(row['18点-24点维护']) if pd.notna(row['18点-24点维护']) else 0,
        int(row['00点后待客']) if pd.notna(row['00点后待客']) else 0,
        int(row['00点后维护']) if pd.notna(row['00点后维护']) else 0,
        int(row['晚场待客最高峰台数']) if pd.notna(row['晚场待客最高峰台数']) else 0,
        str(row['晚场待客最高峰时点']) if pd.notna(row['晚场待客最高峰时点']) else '',
        int(row['全天待客台数']) if pd.notna(row['全天待客台数']) else 0,
        float(row['总计营业额']) if pd.notna(row['总计营业额']) else 0
    ]
    
    cursor.execute(insert_sql, values)
    count += 1

conn.commit()
print(f"✓ 成功导入 {count} 条数据")

# 5. 验证数据
print("\n5. 验证导入的数据...")
cursor.execute("""
SELECT data_date, COUNT(*) as store_count
FROM store_daily 
WHERE data_date BETWEEN '2026-05-01' AND '2026-05-13'
GROUP BY data_date
ORDER BY data_date
""")

results = cursor.fetchall()
print("\n日期数据统计:")
for row in results:
    print(f"  {row['data_date']}: {row['store_count']} 家门店")

cursor.close()
conn.close()

print("\n✅ 数据导入完成！")
