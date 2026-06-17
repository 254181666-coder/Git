#!/usr/bin/env python3
import pymysql
import pandas as pd

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='root', 
    password='CHANGE_ME_MYSQL_PASSWORD', 
    database='ktv_analysis', 
    charset='utf8mb4'
)

print("=" * 80)
print("松原一店数据诊断")
print("=" * 80)

print("\n【1】查看 stores 表中的门店列表")
query = "SELECT id, store_name FROM stores ORDER BY id"
df_stores = pd.read_sql(query, conn)
print("\n所有门店:")
for _, row in df_stores.iterrows():
    print(f"  ID: {row['id']}, 名称: {row['store_name']}")

print("\n【2】查找包含 '松原' 的门店")
query = "SELECT id, store_name FROM stores WHERE store_name LIKE '%松原%'"
df_songyuan = pd.read_sql(query, conn)
print("\n查找结果:")
for _, row in df_songyuan.iterrows():
    print(f"  ID: {row['id']}, 名称: {row['store_name']}")

print("\n【3】查看 store_daily 表中的门店分布")
query = """
SELECT 
    s.store_name,
    COUNT(*) as record_count,
    MIN(sd.data_date) as min_date,
    MAX(sd.data_date) as max_date
FROM store_daily sd
JOIN stores s ON sd.store_id = s.id
GROUP BY s.store_name
ORDER BY s.store_name
"""
df_distribution = pd.read_sql(query, conn)
print("\n门店数据记录:")
for _, row in df_distribution.iterrows():
    print(f"  {row['store_name']}: {row['record_count']}条 ({row['min_date']} 至 {row['max_date']})")

print("\n【4】查看 stored_value 表中的门店分布")
query = """
SELECT 
    s.store_name,
    COUNT(*) as record_count,
    MIN(sv.data_date) as min_date,
    MAX(sv.data_date) as max_date
FROM stored_value sv
JOIN stores s ON sv.store_id = s.id
GROUP BY s.store_name
ORDER BY s.store_name
"""
df_stored_distribution = pd.read_sql(query, conn)
print("\n储值数据记录:")
for _, row in df_stored_distribution.iterrows():
    print(f"  {row['store_name']}: {row['record_count']}条 ({row['min_date']} 至 {row['max_date']})")

print("\n【5】查看所有门店在 store_daily 表中的完整记录")
query = """
SELECT DISTINCT s.store_name, s.id as store_id
FROM store_daily sd
RIGHT JOIN stores s ON sd.store_id = s.id
ORDER BY s.store_name
"""
df_all_stores = pd.read_sql(query, conn)
print("\n门店在 store_daily 表中的情况:")
for _, row in df_all_stores.iterrows():
    has_data = "✅ 有数据" if pd.notna(row['store_name']) else "❌ 无数据"
    print(f"  {row['store_name']} (ID: {row['store_id']}): {has_data}")

print("\n【6】查找松原一店相关的原始数据")
if not df_songyuan.empty:
    songyuan_id = df_songyuan.iloc[0]['id']
    songyuan_name = df_songyuan.iloc[0]['store_name']
    
    print(f"\n查找 {songyuan_name} (ID: {songyuan_id}) 的数据")
    
    query = f"""
    SELECT COUNT(*) as count, MIN(data_date), MAX(data_date)
    FROM store_daily
    WHERE store_id = {songyuan_id}
    """
    df_count = pd.read_sql(query, conn)
    print(f"\nstore_daily 表记录数: {df_count.iloc[0]['count']}")
    if df_count.iloc[0]['count'] > 0:
        print(f"日期范围: {df_count.iloc[0]['MIN(data_date)']} 至 {df_count.iloc[0]['MAX(data_date)']}")
    
    query = f"""
    SELECT COUNT(*) as count, MIN(data_date), MAX(data_date)
    FROM stored_value
    WHERE store_id = {songyuan_id}
    """
    df_stored_count = pd.read_sql(query, conn)
    print(f"\nstored_value 表记录数: {df_stored_count.iloc[0]['count']}")
    if df_stored_count.iloc[0]['count'] > 0:
        print(f"日期范围: {df_stored_count.iloc[0]['MIN(data_date)']} 至 {df_stored_count.iloc[0]['MAX(data_date)']}")
    
    query = f"""
    SELECT *
    FROM store_daily
    WHERE store_id = {songyuan_id}
    LIMIT 10
    """
    df_sample = pd.read_sql(query, conn)
    print(f"\nstore_daily 样例数据 (前10条):")
    print(df_sample[['data_date', 'total_revenue', 'actual_amount', 'stored_card_sales']])

conn.close()
