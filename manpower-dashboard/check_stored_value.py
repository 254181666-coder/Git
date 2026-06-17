"""检查 stored_value 表"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

sv_df = query("SELECT * FROM stored_value LIMIT 10")
print("=== stored_value 列名:", sv_df.columns.tolist())
print("\n=== 前10条:", sv_df)

print("\n=== 2025年的数据:", query("SELECT COUNT(*) FROM stored_value WHERE data_date BETWEEN '2025-04-01' AND '2025-04-30'").iloc[0,0])
print("=== 2026年的数据:", query("SELECT COUNT(*) FROM stored_value WHERE data_date BETWEEN '2026-04-01' AND '2026-04-30'").iloc[0,0])
