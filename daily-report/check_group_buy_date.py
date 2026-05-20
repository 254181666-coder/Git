
#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

GROUP_BUY_DIR = Path("/Users/ann/Desktop/团购")

print("=" * 80)
print("检查团购数据日期范围")
print("=" * 80)
print()

store_names = ['佳木斯', '安达', '晨宇', '松原一', '松原二', '榆树', '法库', '锡盟', '鸡西']

for store_name in store_names:
    for platform in ['美团', '抖音']:
        file_path = GROUP_BUY_DIR / f"{store_name}{platform}.xlsx"
        if file_path.exists():
            try:
                df = pd.read_excel(file_path)
                print(f"【{store_name} - {platform}】")
                print(f"  总行数: {len(df)}")
                
                # 检查日期列
                date_col = None
                if platform == '美团':
                    date_cols = ['消费时间', '验证时间']
                else:
                    date_cols = ['下单时间', '支付时间', '核销时间']
                
                for col in date_cols:
                    if col in df.columns:
                        try:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                            valid_dates = df[col].dropna()
                            if len(valid_dates) > 0:
                                date_col = col
                                min_date = valid_dates.min()
                                max_date = valid_dates.max()
                                print(f"  日期列: {date_col}")
                                print(f"  日期范围: {min_date} ~ {max_date}")
                                break
                        except Exception as e:
                            continue
                
                if not date_col:
                    print(f"  未找到有效日期列")
                    print(f"  所有列: {list(df.columns)}")
                
                print()
            except Exception as e:
                print(f"【{store_name} - {platform}】读取失败: {e}")
                print()

print("检查完成！")

