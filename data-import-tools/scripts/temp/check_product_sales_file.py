
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG
import pymysql

def main():
    print("=" * 80)
    print("检查商品销售文件结构")
    print("=" * 80)

    # 先检查数据库中 product_sales_summary 的结构
    print("\n📊 product_sales_summary 表结构:")
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DESCRIBE product_sales_summary")
    for row in cursor.fetchall():
        print(f"   {row[0]}")

    # 查看前几行数据
    print("\n📊 前 10 行数据:")
    cursor.execute("SELECT * FROM product_sales_summary LIMIT 10")
    columns = [desc[0] for desc in cursor.description]
    print(f"   列名: {columns}")
    for i, row in enumerate(cursor.fetchall()):
        print(f"   行 {i+1}: {row}")
    cursor.close()
    conn.close()

    # 检查归档中的文件内容
    print("\n📁 检查归档文件内容:")
    archive_dir = Path(PROJECT_ROOT) / "data" / "archive" / "source_2026_05_02"
    for f in archive_dir.glob("商品销售汇总*.xlsx"):
        print(f"\n   文件: {f.name}")
        df = pd.read_excel(f, nrows=5)
        print(f"   列名: {df.columns.tolist()}")
        print(f"   前3行:\n{df.head(3).to_string()}")

    print("\n" + "=" * 80)
    print("检查完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

