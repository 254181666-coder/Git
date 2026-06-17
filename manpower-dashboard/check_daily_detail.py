"""检查 daily_detail 表"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import query

print("检查 daily_detail 表...")
try:
    sample = query("SELECT * FROM daily_detail LIMIT 5")
    print("列名:")
    print(list(sample.columns))
    print("\n数据:")
    print(sample)

    print("\n检查分组统计...")
    stats = query("""
        SELECT data_date, store_name, COUNT(*) as cnt
        FROM daily_detail
        GROUP BY data_date, store_name
        ORDER BY data_date DESC
        LIMIT 10
    """)
    print(stats)
except Exception as e:
    print(f"错误: {e}")
