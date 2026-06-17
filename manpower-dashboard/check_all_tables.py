
"""快速检查所有表结构"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query

print("=== 所有表名称 ===")
all_tables = query("SHOW TABLES")
for table in all_tables.iloc[:,0]:
    print(f"\n--- {table} ---")
    try:
        info = query(f"SELECT * FROM {table} LIMIT 3")
        print(f"列: {info.columns.tolist()}")
        print(f"行数: {len(info)}")
        if len(info) > 0:
            print(f"前1-2行: {info.head(2)}")
    except Exception as e:
        print(f"错误: {e}")
