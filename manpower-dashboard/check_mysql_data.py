"""全面诊断MySQL数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.config import USE_MYSQL, MYSQL_CONFIG
from src.database import query, get_engine

print("=== 数据库配置 ===")
print(f"USE_MYSQL: {USE_MYSQL}")
if USE_MYSQL:
    print(f"MySQL: {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")

print(f"\n=== 检查数据库表 ===")
if USE_MYSQL:
    tables_df = query("SHOW TABLES")
else:
    tables_df = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print(tables_df)
available_tables = tables_df.iloc[:,0].tolist()
print(f"\n可用表: {available_tables}")

print(f"\n=== 检查各表数据行数 ===")
tables_to_check = ['store_daily', 'product_sales', 'stored_value', 'stores', 'product_commission', 'stored_commission']
for table in tables_to_check:
    try:
        if table in available_tables:
            cnt_df = query(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cnt_df.iloc[0,0]
            min_max = ""
            try:
                if table in ['store_daily', 'product_sales', 'stored_value']:
                    min_max_df = query(f"SELECT MIN(data_date) as min_date, MAX(data_date) as max_date FROM {table}")
                    min_date = min_max_df.iloc[0,0]
                    max_date = min_max_df.iloc[0,1]
                    min_max = f", 日期范围: {min_date} ~ {max_date}"
            except:
                pass
            print(f"✅ {table}: {cnt} 条 {min_max}")
        else:
            print(f"❌ {table}: 不存在")
    except Exception as e:
        print(f"❌ {table}: {str(e)}")

print(f"\n=== 检查product_sales前10行 ===")
if "product_sales" in available_tables:
    ps_sample = query("SELECT * FROM product_sales LIMIT 10")
    print(ps_sample.columns.tolist())
    print(ps_sample)

print(f"\n✅ 诊断完成")
