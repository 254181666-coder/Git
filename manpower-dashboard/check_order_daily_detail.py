
"""检查 order_daily 和 order_detail 的 time_period 字段"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

print("=== order_daily 表 ===")
od_sample = query("SELECT * FROM order_daily LIMIT 20")
print(f"列: {od_sample.columns.tolist()}")
print("\n前15行:")
print(od_sample.head(15))

print("\n\n=== time_period 唯一值 ===")
time_periods = query("SELECT DISTINCT time_period FROM order_daily ORDER BY time_period")
print(time_periods)

print("\n\n=== order_detail 表 ===")
det_sample = query("SELECT * FROM order_detail LIMIT 5")
print(f"列: {det_sample.columns.tolist()}")
print(det_sample)
