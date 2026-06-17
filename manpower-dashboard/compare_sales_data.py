
#!/usr/bin/env python3
"""
对比用户提供的和数据库中的销售数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from src.database import query

os.environ['USE_MYSQL'] = 'true'

print("=" * 80)
print("对比商品销售数据")
print("=" * 80)

# 用户提供的数据
user_data = {
    "2026-04-28": {"count": 8045, "amount": 655936.50},
    "2026-04-26": {"count": 6245, "amount": 243861.21},
    "2026-04-25": {"count": 8523, "amount": 365294.59},
    "2026-04-24": {"count": 7975, "amount": 331299.48},
    "2026-04-23": {"count": 5093, "amount": 204797.61},
    "2026-04-22": {"count": 11857, "amount": 612658.76},
    "2026-04-21": {"count": 10518, "amount": 428552.45},
}

print("\n用户提供的数据（商品销售明细表）:")
print("-" * 80)
for date, data in sorted(user_data.items(), reverse=True):
    print(f"{date}: 记录数={data['count']}, 销售金额={data['amount']}")

# 检查 product_sales 表的数据
print("\n\n数据库 product_sales 表数据:")
print("-" * 80)
sql_sales = """
SELECT data_date, COUNT(*) as db_count,
       SUM(quantity) as db_quantity,
       SUM(sales_amount) as db_amount
FROM product_sales
WHERE data_date IN ('2026-04-28', '2026-04-26', '2026-04-25',
                   '2026-04-24', '2026-04-23', '2026-04-22', '2026-04-21')
GROUP BY data_date
ORDER BY data_date DESC
"""
df_sales = query(sql_sales)
print(df_sales.to_string())

print("\n\n按大分类查看 product_sales 2026-04-26 的数据:")
print("-" * 80)
sql_cat = """
SELECT data_date, big_category,
       COUNT(*) as count,
       SUM(quantity) as quantity,
       SUM(sales_amount) as amount
FROM product_sales
WHERE data_date = '2026-04-26'
GROUP BY data_date, big_category
ORDER BY amount DESC
"""
df_cat = query(sql_cat)
print(df_cat.to_string())

print("\n\n对比结果:")
print("-" * 80)
for _, row in df_sales.iterrows():
    date = str(row['data_date'])
    if date in user_data:
        user_count = user_data[date]['count']
        user_amount = user_data[date]['amount']
        db_count = row['db_count']
        db_amount = row['db_amount']
        
        count_ok = abs(db_count - user_count) < 100
        amount_ok = abs(db_amount - user_amount) < 1000
        
        status = "✅ OK" if (count_ok and amount_ok) else "❌ 异常"
        
        print(f"{status} {date}:")
        print(f"   记录数: 用户={user_count}, 数据库={db_count}, 差异={abs(db_count-user_count)}")
        print(f"   金额: 用户={user_amount:.2f}, 数据库={db_amount:.2f}, 差异={abs(db_amount-user_amount):.2f}")

print("\n" + "=" * 80)
