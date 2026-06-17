
"""检查order_daily表的完整数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

print("=== order_daily 全量时段统计 ===")
sql = """
    SELECT
        data_date,
        store_name,
        time_period,
        count(*) as cnt,
        sum(revenue) as rev,
        sum(item_count) as items
    FROM order_daily
    WHERE data_date BETWEEN '2026-04-20' AND '2026-04-28'
    GROUP BY data_date, store_name, time_period
    ORDER BY data_date, store_name, time_period
"""
result = query(sql)
print(result)

print("\n=== 按时段单独统计 ===")
sql2 = """
    SELECT time_period, count(*), sum(revenue)
    FROM order_daily
    GROUP BY time_period
"""
print(query(sql2))
