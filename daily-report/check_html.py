
#!/usr/bin/env python3
"""
直接检查HTML文件中上东开机套餐的内容
"""
from pathlib import Path

html_file = Path("/Users/ann/Desktop/AI/Project/每日报告/data/output/团购月度报告_2026-05-01_2026-05-10.html")

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到包含"上东"和"开机套餐"的行
lines = content.split('\n')
for i, line in enumerate(lines):
    if '上东' in line and ('开机套餐' in line or '日场开机套餐' in line):
        print(f"行{i}: {line[:200]}")
        # 打印前后几行
        for j in range(max(0, i-2), min(len(lines), i+3)):
            print(f"  {j}: {lines[j][:200]}")
        print()
