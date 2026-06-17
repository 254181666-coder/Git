"""测试经营总览页面数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.components.business_dashboard import load_core_data, load_product_category_data, get_available_dates

print("=== 测试经营总览数据加载 ===\n")

print("1. 获取可用日期范围...")
try:
    min_date, max_date = get_available_dates()
    print(f"   日期范围: {min_date} ~ {max_date}")
except Exception as e:
    print(f"   ❌ 错误: {e}")
    sys.exit(1)

print(f"\n2. 测试加载核心数据 ({min_date} ~ {max_date})...")
try:
    df = load_core_data(min_date, max_date)
    print(f"   ✅ 加载成功! 数据量: {len(df)} 条")
    print(f"   列名: {list(df.columns)}")
    
    if len(df) > 0:
        print(f"\n   预览:")
        print(df.head())
        
        total_revenue = df['revenue'].sum()
        print(f"\n   总营业额: {total_revenue:.2f}")
        
except Exception as e:
    print(f"   ❌ 错误: {e}")
    import traceback
    print(f"\n{traceback.format_exc()}")

print(f"\n3. 测试加载商品分类数据...")
try:
    product_df = load_product_category_data(min_date, max_date)
    print(f"   ✅ 加载成功! 数据量: {len(product_df)} 条")
    print(f"   列名: {list(product_df.columns)}")
    
    if len(product_df) > 0:
        print(f"\n   预览:")
        print(product_df.head())
except Exception as e:
    print(f"   ❌ 错误: {e}")
    import traceback
    print(f"\n{traceback.format_exc()}")

print("\n=== 测试完成 ===")
