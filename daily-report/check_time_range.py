
#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from src.database import query

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")

print("=" * 80)
print("检查数据时间范围")
print("=" * 80)

print("\n【去年数据 - Excel文件】")
for store in ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']:
    for platform in ['美团', '抖音']:
        file_path = GROUP_BUY_DIR / f"{store}{platform}.xlsx"
        if file_path.exists():
            df = pd.read_excel(file_path)
            time_col = None
            if platform == '美团' and '消费时间' in df.columns:
                time_col = '消费时间'
            elif platform == '抖音' and '下单时间' in df.columns:
                time_col = '下单时间'
            
            if time_col:
                df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
                df = df.dropna(subset=[time_col])
                if len(df) > 0:
                    min_date = df[time_col].min().strftime('%Y-%m-%d')
                    max_date = df[time_col].max().strftime('%Y-%m-%d')
                    print(f"  {store}{platform}: {min_date} ~ {max_date}, {len(df)}条")

print("\n\n【今年数据 - 数据库】")
df_orders = query("SELECT DISTINCT data_date FROM order_detail ORDER BY data_date")
print(f"  数据库data_date范围:")
for d in df_orders['data_date'].tolist():
    print(f"    {d}")

print("\n  2026年5月团购数据:")
df_may = query("""
    SELECT data_date, COUNT(*) as cnt, SUM(actual_amount) as amt
    FROM order_detail
    WHERE data_date >= '2026-05-01' AND data_date <= '2026-05-31'
    AND source_channel IN ('抖音', '美团大众', '线下团购')
    GROUP BY data_date
    ORDER BY data_date
""")
for _, row in df_may.iterrows():
    print(f"    {row['data_date']}: {row['cnt']}单, {row['amt']:.0f}元")
