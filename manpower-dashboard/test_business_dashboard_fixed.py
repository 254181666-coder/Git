"""测试修复后的经营总览"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from src.components.business_dashboard import load_product_top_data, get_available_dates

print("=== 测试修复后的经营总览 ===\n")

min_date, max_date = get_available_dates()
print(f"日期范围: {min_date} ~ {max_date}\n")

df_product = load_product_top_data(str(min_date), str(max_date))
print(f"✅ 成功加载 {len(df_product)} 条商品数据!\n")

print("列名:")
print(df_product.columns.tolist())

print("\n前5条预览:")
print(df_product.head())

product_total = df_product.groupby(['product_name', 'big_category']).agg({
    'quantity': 'sum',
    'total': 'sum'
}).reset_index()
product_top10 = product_total.sort_values('total', ascending=False).head(10)

print("\n\n🏆 TOP10 商品:")
print(product_top10)

print("\n✅ 经营总览修复成功！")
