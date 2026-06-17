"""测试 get_commission_data"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.components.staff_efficiency import get_commission_data

# 用一个有数据的日期范围
min_date = '2026-04-01'
max_date = '2026-04-28'

df_p, df_s = get_commission_data(min_date, max_date)
print("=== get_commission_data 结果 ===")
print(f"product_commission: {len(df_p)}")
print(f"stored_commission: {len(df_s)}")
if not df_p.empty:
    print("\nproduct_commission 前3条:")
    print(df_p.head(3))
if not df_s.empty:
    print("\nstored_commission 前3条:")
    print(df_s.head(3))
