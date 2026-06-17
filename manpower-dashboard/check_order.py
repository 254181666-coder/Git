from src.database import query

# 看一个门店的数据，确认客单价计算是否正确
# 客单价 = revenue / customers（而不是 revenue / item_count）
print('=== 佳木斯店 4月1日 按小时段客单价分析 ===')
print()

# 当前代码用 revenue / item_count 作为客单价
# 但 item_count 是开房单数量，不是顾客数
# store_daily 中的 customers 才是正确的顾客数
print('order_daily 4月1日:')
df = query('SELECT store_name, time_period, item_count, revenue, revenue/item_count as price_per_item FROM order_daily WHERE data_date = "2026-04-01" AND store_name = "佳木斯店"')
print(df)
print()

print('store_daily 4月1日:')
df2 = query('SELECT s.store_name, sd.revenue/10 as rev_yuan, sd.customers, (sd.revenue/10)/sd.customers as price_per_customer FROM store_daily sd JOIN stores s ON sd.store_id = s.id WHERE sd.data_date = "2026-04-01" AND s.store_name = "佳木斯店"')
print(df2)

# 问题：item_count 是开房单数量还是商品数量？
# 看4月1日佳木斯店：日场56单 1277.92元，午夜场12单 607.25元
# 日场客单价 = 1277.92/56 = 22.8元/单
# 这看起来不对，应该远高于此

print()
print('=== item_count 是什么？查看轻舟日报确认 ===')
# 查看是否有轻舟日报API的数据
df3 = query('SELECT * FROM qingzhou_report LIMIT 1')
print(df3)
