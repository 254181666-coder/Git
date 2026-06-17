import pandas as pd
from src.database import query
from src.components.room_sales import load_room_product_data, get_big_category

# 验证修复后的包房数量
start_date = '2026-04-01'
end_date = '2026-04-30'

df = load_room_product_data(start_date, end_date)

print('=== 全部门店包房数量统计 ===')
for store in sorted(df['门店'].unique()):
    store_df = df[df['门店'] == store]
    room_count = store_df['包厢'].nunique()
    print(f'{store}: {room_count}个包房')

print()
print('=== 上东店包房样本 ===')
shangdong = df[df['门店'] == '上东店']
rooms = shangdong['包厢'].unique()
print(f'包房总数: {len(rooms)}')
print(f'前20个包房: {list(rooms[:20])}')

print()
print('=== 法库店包房样本 ===')
faku = df[df['门店'] == '法库店']
rooms = faku['包厢'].unique()
print(f'包房总数: {len(rooms)}')
print(f'所有包房: {list(rooms)}')
