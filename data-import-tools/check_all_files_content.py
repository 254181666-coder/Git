#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
downloads_dir = Path("/Users/ann/Downloads")

print("检查所有下载文件的内容日期：")
print("-" * 80)

# 检查所有相关文件
patterns = [
    "日营业数据表*.xlsx",
    "会员储值订单表*.xlsx",
    "商品销售明细*.xlsx",
    "商品销售汇总*.xlsx",
    "储值提成明细表*.xlsx",
    "商品提成明细表*.xlsx",
    "会员余额变动明细*.xlsx"
]

for pattern in patterns:
    files = list(downloads_dir.glob(pattern))
    for f in sorted(files):
        print(f"\n{f.name}:")
        try:
            df = pd.read_excel(f)
            found_date = None
            
            # 尝试不同的列名
            date_columns = ['日期', '销售日期', '充值时间', '销售日期::multi-filter']
            for col in date_columns:
                if col in df.columns:
                    dates = df[col].dropna()
                    if len(dates) > 0:
                        try:
                            # 尝试获取第一个非空日期
                            first_date = dates.iloc[0]
                            if pd.notna(first_date):
                                # 转换为日期字符串
                                if hasattr(first_date, 'strftime'):
                                    found_date = first_date.strftime('%Y-%m-%d')
                                else:
                                    # 尝试转换
                                    dt = pd.to_datetime(first_date)
                                    found_date = dt.strftime('%Y-%m-%d')
                                break
                        except Exception as e:
                            continue
            
            if found_date:
                print(f"  内容日期：{found_date}")
                # 检查是否有门店列
                if '门店' in df.columns or '门店名称' in df.columns:
                    store_col = '门店' if '门店' in df.columns else '门店名称'
                    stores = df[store_col].dropna()
                    valid_stores = [s for s in stores if str(s).strip() != '合计']
                    print(f"  门店数量：{len(valid_stores)}")
            else:
                print(f"  未找到日期列，列名有：{list(df.columns)}")
        except Exception as e:
            print(f"  读取失败：{e}")
