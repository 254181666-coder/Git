
#!/usr/bin/env python3
"""
直接检查HTML文件中上东开机套餐的内容 - 搜索表格数据
"""
from pathlib import Path

html_file = Path("/Users/ann/Desktop/AI/Project/每日报告/data/output/团购月度报告_2026-05-01_2026-05-10.html")

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到"套餐详情"部分
if '套餐详情' in content:
    idx = content.find('套餐详情')
    print(f"找到'套餐详情'位置: {idx}")
    print(f"\n该位置前后500字符:")
    print(content[max(0, idx-100):idx+500])
else:
    print("未找到'套餐详情'")
    
# 搜索所有包含"开机套"的内容
import re
matches = re.findall(r'.{0,100}开机套.{0,100}', content)
print(f"\n\n找到 {len(matches)} 处包含'开机套':")
for m in matches[:5]:
    print(f"  {m}")
