"""测试经营总览 MySQL 数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.components.business_dashboard import load_core_data, get_available_dates

print("=== 经营总览 MySQL 数据测试 ===\n")

min_date, max_date = get_available_dates()
print(f"可用日期范围: {min_date} ~ {max_date}\n")

df = load_core_data(str(min_date), str(max_date))
print(f"数据行数: {len(df)}\n")
print("数据样本:")
print(df.head())

print(f"\n✅ 数据加载成功！")
