#!/usr/bin/env python3
import pandas as pd

file_path = '各店面备品统计.xlsx'
df = pd.read_excel(file_path, sheet_name='Sheet1', header=None)

print("前25行完整数据:")
for i in range(min(25, len(df))):
    print(f"行 {i}: {df.iloc[i].tolist()}")
