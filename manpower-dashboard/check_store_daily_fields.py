"""检查store_daily表的所有字段"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

sd_sample = query("SELECT * FROM store_daily LIMIT 5")
print("=== store_daily 列名:\n", sd_sample.columns.tolist())
print("\n=== 前几条数据示例:")
print(sd_sample)
