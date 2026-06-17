
"""
测试MySQL连接
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import USE_MYSQL
print(f"当前USE_MYSQL设置: {USE_MYSQL}")
print()

if USE_MYSQL:
    from src.database import query
    print("=== 测试MySQL连接 ===\n")
    
    try:
        sql = """
        SELECT DISTINCT data_date
        FROM store_daily
        WHERE data_date BETWEEN '2026-04-01' AND '2026-04-30'
        ORDER BY data_date
        """
        df = query(sql)
        print(f"✅ MySQL连接成功！")
        print(f"store_daily表中有数据的日期:")
        for date in df['data_date']:
            print(f"  - {date}")
        
        print(f"\n\n=== 检查4月25日数据 ===\n")
        sql2 = """
        SELECT sd.data_date, s.store_name, sd.revenue, sd.customers
        FROM store_daily sd
        JOIN stores s ON s.id = sd.store_id
        WHERE sd.data_date = '2026-04-25'
        LIMIT 10
        """
        df2 = query(sql2)
        print(f"4月25日有 {len(df2)} 条store_daily记录")
        if not df2.empty:
            print(df2)
            
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        import traceback
        traceback.print_exc()

