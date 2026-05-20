
#!/usr/bin/env python3
"""
提取HTML中上东开机套餐的完整内容
"""
from pathlib import Path
import re

html_file = Path("/Users/ann/Desktop/AI/Project/每日报告/data/output/团购月度报告_2026-05-01_2026-05-10.html")

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到上东表格中的开机套餐
pattern = r'<h3>上东</h3><table>.*?</table>'
match = re.search(pattern, content, re.DOTALL)

if match:
    table = match.group(0)
    print("【上东门店的套餐详情表】")
    print(table[:3000])
else:
    print("未找到上东表格")
