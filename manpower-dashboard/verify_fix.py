import pandas as pd
from src.database import query
from src.utils import normalize_store_name

# 模拟修复后的逻辑验证
sql_sv = """
    SELECT sv.data_date, sv.recharge_time, s.store_name, sv.stored_amount, sv.drink_principal
    FROM stored_value sv
    JOIN stores s ON s.id = sv.store_id
"""
df_stored = query(sql_sv)
df_stored['data_date'] = pd.to_datetime(df_stored['data_date'])
df_stored['recharge_time'] = pd.to_datetime(df_stored['recharge_time'], errors='coerce')
df_stored['stored_amount'] = pd.to_numeric(df_stored['stored_amount'], errors='coerce').fillna(0)
df_stored['drink_principal'] = pd.to_numeric(df_stored['drink_principal'], errors='coerce').fillna(0)
df_stored['门店'] = df_stored['store_name'].apply(normalize_store_name)
df_stored = df_stored[df_stored['门店'] != '临河街店']

month_value = 4

# 2025年按data_date筛选
df_stored_25 = df_stored[df_stored['data_date'].dt.year == 2025]
df_25_stored = df_stored_25[df_stored_25['data_date'].dt.month == month_value].copy()

# 2026年按recharge_time筛选
df_stored_26 = df_stored[df_stored['recharge_time'].dt.year == 2026]
df_26_stored = df_stored_26[df_stored_26['recharge_time'].dt.month == month_value].copy()

print('=== 2025年4月储值卡统计（按data_date）===')
print(f'记录数: {len(df_25_stored)}')
print(f'总金额(stored_amount): {df_25_stored["stored_amount"].sum():,.0f}')

print()
print('=== 2026年4月储值卡统计（按recharge_time）===')
print(f'记录数: {len(df_26_stored)}')
print(f'总金额(drink_principal): {df_26_stored["drink_principal"].sum():,.0f}')

print()
print('=== 2026年4月储值卡按日分布（按recharge_time）===')
df_26_stored['日期'] = df_26_stored['recharge_time'].dt.strftime('%m-%d')
daily = df_26_stored.groupby('日期')['drink_principal'].agg(['count', 'sum']).reset_index()
print(daily)
