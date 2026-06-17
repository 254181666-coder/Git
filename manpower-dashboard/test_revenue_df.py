"""测试 revenue_df 数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.components.business_overview import load_revenue_data
from src.database import query

# 先测试 business_overview 的 load_revenue_data
min_date, max_date = query("SELECT MIN(data_date) as min_date, MAX(data_date) as max_date FROM store_daily").iloc[0]
print(f"日期: {min_date} ~ {max_date}")
df_rev = load_revenue_data(str(min_date), str(max_date))
print("\n\n=== revenue_df 列名:", df_rev.columns.tolist())
print("\n\n=== revenue_df 前10条:")
print(df_rev.head(10))
