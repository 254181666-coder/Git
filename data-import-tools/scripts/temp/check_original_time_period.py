
#!/usr/bin/env python3
"""
检查原始 order_export.csv 文件里的开房时段字段
"""
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
archive_root = PROJECT_ROOT / 'data' / 'archive'

test_file = archive_root / 'source_2026_04_25' / 'order_export_19351_20260425093321.csv'

print("检查原始文件里的开房时段字段...")

df = pd.read_csv(test_file, encoding='gbk', nrows=50)

print("\n前10行数据的开房时段：")
for i, row in df.head(10).iterrows():
    print(f"  {i}: {row.get('开房时段')}")

print("\n所有不同的时段值：")
print(df['开房时段'].value_counts())

print(f"\n总行数: {len(df)}")
