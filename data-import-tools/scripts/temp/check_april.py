#!/usr/bin/env python3
import pymysql
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print('=' * 60)
print('4月份会员储值订单数据检查')
print('=' * 60)

# 总记录数
cursor.execute("SELECT COUNT(*) FROM stored_value WHERE data_date >= '2026-04-01' AND data_date < '2026-05-01'")
total_april = cursor.fetchone()[0]
print(f'\n4月份总记录: {total_april}')

# 有数据的日期
cursor.execute('''
    SELECT DISTINCT DATE(data_date) as dt 
    FROM stored_value
    WHERE data_date >= "2026-04-01" AND data_date < "2026-05-01"
    ORDER BY dt
''')
dates = [r[0] for r in cursor.fetchall()]
print(f'\n有数据的日期: {dates}')

# 每天记录数
print(f'\n每天记录数:')
cursor.execute('''
    SELECT DATE(data_date) as dt, COUNT(*) as cnt
    FROM stored_value
    WHERE data_date >= \"2026-04-01\" AND data_date < \"2026-05-01\"
    GROUP BY dt
    ORDER BY dt
''')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条')

# 按门店
print(f'\n按门店统计:')
cursor.execute('''
    SELECT s.store_name, COUNT(*) as cnt
    FROM stored_value v
    JOIN stores s ON v.store_id = s.id
    WHERE v.data_date >= \"2026-04-01\" AND v.data_date < \"2026-05-01\"
    GROUP BY s.store_name
''')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]} 条')

print('\n' + '=' * 60)
print('检查完成！')
print('=' * 60)

cursor.close()
conn.close()
