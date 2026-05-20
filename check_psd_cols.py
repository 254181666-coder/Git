
#!/usr/bin/env python3
"""
检查product_sales_detail表的列名
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query

sql = "SHOW COLUMNS FROM product_sales_detail"
df = query(sql)
print("product_sales_detail 列名:")
for _, row in df.iterrows():
    print(f"  {row['Field']}")
