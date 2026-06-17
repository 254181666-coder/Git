
"""测试提成员工人数统计"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.database import query
from src.utils import normalize_store_name

min_date, max_date = query("SELECT MIN(data_date) as min_date, MAX(data_date) as max_date FROM store_daily").iloc[0]
start_date = str(min_date)
end_date = str(max_date)

print(f"日期: {start_date} ~ {end_date}")

print("\n=== product_commission 数据 ===")
pc_data = query("""
    SELECT s.store_name, pc.commission_staff as employee_name, 
           SUM(pc.commission_amount) as total_commission
    FROM product_commission pc
    JOIN stores s ON pc.store_id = s.id
    WHERE pc.business_date BETWEEN ? AND ?
    GROUP BY s.store_name, pc.commission_staff
""", (start_date, end_date))
print(f"行数: {len(pc_data)}")
print(pc_data.head(10))

print("\n=== stored_commission 数据 ===")
sc_data = query("""
    SELECT s.store_name, sc.commission_staff as employee_name, 
           SUM(sc.commission_amount) as total_commission
    FROM stored_commission sc
    JOIN stores s ON sc.store_id = s.id
    WHERE sc.business_date BETWEEN ? AND ?
    GROUP BY s.store_name, sc.commission_staff
""", (start_date, end_date))
print(f"行数: {len(sc_data)}")
print(sc_data.head(10))

print("\n=== 合并后数据 ===")
if not pc_data.empty:
    pc_data['store_name'] = pc_data['store_name'].apply(normalize_store_name)
if not sc_data.empty:
    sc_data['store_name'] = sc_data['store_name'].apply(normalize_store_name)
merged = []
if not pc_data.empty:
    merged.append(pc_data)
if not sc_data.empty:
    merged.append(sc_data)
if merged:
    merged_df = pd.concat(merged, ignore_index=True)
    print(merged_df.head(10))
    counts = merged_df.groupby('store_name').agg(
        emp_count=('employee_name', 'nunique')
    ).reset_index()
    print("\n=== 各门店有提成人数 ===")
    print(counts)
else:
    print("没有数据")
