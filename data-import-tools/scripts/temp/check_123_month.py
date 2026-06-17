#!/usr/bin/env python3
import pymysql
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

print("=== 检查每月数据情况 ===")

# 检查1月
cursor.execute("SELECT COUNT(*) FROM stored_value WHERE data_date >= '2026-01-01' AND data_date < '2026-02-01'")
jan = cursor.fetchone()[0]
print(f"1月: {jan} 条")

# 检查2月
cursor.execute("SELECT COUNT(*) FROM stored_value WHERE data_date >= '2026-02-01' AND data_date < '2026-03-01'")
feb = cursor.fetchone()[0]
print(f"2月: {feb} 条")

# 检查3月
cursor.execute("SELECT COUNT(*) FROM stored_value WHERE data_date >= '2026-03-01' AND data_date < '2026-04-01'")
mar = cursor.fetchone()[0]
print(f"3月: {mar} 条")

print(f"\n总计(1-3月): {jan+feb+mar} 条")

# 对比备份里的1-3月记录数
print("\n=== 备份Excel文件里的1-3月记录 ===")
print("会员储值订单表_2026_04_24.xlsx (1月): 6094 行")
print("会员储值订单表_2026_04_24 (1).xlsx (2月): 8384 行")
print("会员储值订单表_2026_04_24 (2).xlsx (3月): 3377 行")
print("备份总计(1-3月): 17855 行")

cursor.close()
conn.close()
