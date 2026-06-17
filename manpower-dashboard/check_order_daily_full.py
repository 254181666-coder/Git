
"""检查order_daily完整时段数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

print("=== order_daily所有时段统计 ===")
all_periods = query("""
    SELECT time_period, COUNT(*) as cnt, SUM(revenue) as rev
    FROM order_daily
    GROUP BY time_period
    ORDER BY time_period
""")
print(all_periods)

print("\n=== 各门店各时段分布 ===")
store_period = query("""
    SELECT store_name, time_period, COUNT(*) as cnt
    FROM order_daily
    GROUP BY store_name, time_period
    ORDER BY store_name, time_period
""")
print(store_period)

print("\n=== 完整数据查看 ===")
full = query("SELECT * FROM order_daily LIMIT 50")
print(full.columns.tolist())
print(full)
