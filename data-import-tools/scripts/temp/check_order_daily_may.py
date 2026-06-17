#!/usr/bin/env python3
"""检查5月份order_daily和order_detail数据情况"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("检查5月份数据情况")
print("=" * 80)

# 1. 检查order_detail表中的5月数据
print("\n【1】order_detail表中的5月数据：")
cursor.execute('''
SELECT MIN(data_date), MAX(data_date), COUNT(*)
FROM order_detail
WHERE data_date >= '2026-05-01'
''')
min_date, max_date, count_detail = cursor.fetchone()
print(f"   日期范围：{min_date} 至 {max_date}")
print(f"   总记录数：{count_detail}")

# 按日期统计order_detail
print("\n   按日期统计：")
cursor.execute('''
SELECT data_date, COUNT(*) as cnt
FROM order_detail
WHERE data_date >= '2026-05-01'
GROUP BY data_date
ORDER BY data_date
''')
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]} 条")

# 2. 检查order_daily表中的5月数据
print("\n【2】order_daily表中的5月数据：")
cursor.execute('''
SELECT MIN(data_date), MAX(data_date), COUNT(*)
FROM order_daily
WHERE data_date >= '2026-05-01'
''')
min_date, max_date, count_daily = cursor.fetchone()
print(f"   日期范围：{min_date} 至 {max_date}")
print(f"   总记录数：{count_daily}")

# 按日期统计order_daily
print("\n   按日期统计：")
cursor.execute('''
SELECT data_date, COUNT(*) as cnt
FROM order_daily
WHERE data_date >= '2026-05-01'
GROUP BY data_date
ORDER BY data_date
''')
daily_by_date = {}
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]} 条")
    daily_by_date[row[0]] = row[1]

# 3. 对比缺失的日期
print("\n【3】检查缺失的日期（5月1日至今）：")
start_date = datetime(2026, 5, 1).date()
today = datetime.now().date()
current_date = start_date

missing_in_detail = []
missing_in_daily = []

while current_date <= today:
    # 检查order_detail
    cursor.execute('SELECT COUNT(*) FROM order_detail WHERE data_date = %s', (current_date,))
    cnt = cursor.fetchone()[0]
    if cnt == 0:
        missing_in_detail.append(current_date)
    
    # 检查order_daily
    if current_date not in daily_by_date:
        missing_in_daily.append(current_date)
    
    current_date += timedelta(days=1)

if missing_in_detail:
    print(f"   order_detail表中缺失的日期：{missing_in_detail}")
else:
    print("   order_detail表中5月1日至今的数据完整")

if missing_in_daily:
    print(f"   order_daily表中缺失的日期：{missing_in_daily}")
else:
    print("   order_daily表中5月1日至今的数据完整")

# 4. 检查order_daily表的生成逻辑
print("\n【4】检查order_detail中5月的数据，哪些应该在order_daily中：")
cursor.execute('''
SELECT DISTINCT data_date
FROM order_detail
WHERE data_date >= '2026-05-01'
ORDER BY data_date
''')
detail_dates = [row[0] for row in cursor.fetchall()]
print(f"   order_detail中有数据的日期：{detail_dates}")

cursor.execute('''
SELECT DISTINCT data_date
FROM order_daily
WHERE data_date >= '2026-05-01'
ORDER BY data_date
''')
daily_dates = [row[0] for row in cursor.fetchall()]
print(f"   order_daily中有数据的日期：{daily_dates}")

# 找出order_detail有但order_daily没有的日期
dates_in_detail_not_daily = [d for d in detail_dates if d not in daily_dates]
if dates_in_detail_not_daily:
    print(f"\n   ⚠️  警告：以下日期在order_detail中有数据，但order_daily中缺失：{dates_in_detail_not_daily}")
else:
    print("\n   order_detail和order_daily的日期一致")

# 检查最后几天的日志
print("\n【5】检查最近的导入日志：")
for i in range(1, 6):
    date_str = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
    log_file = PROJECT_ROOT / 'data' / 'logs' / f'import_{date_str}.log'
    if log_file.exists():
        print(f"\n   --- {log_file.name} ---")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-30:]:  # 最后30行
                print(f"   {line.strip()}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
