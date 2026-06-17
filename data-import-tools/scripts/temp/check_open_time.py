#!/usr/bin/env python3
"""专门检查开房时间列的日期"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

source_history_dir = PROJECT_ROOT / "data" / "archive" / "source_history"

print("=" * 80)
print("检查开房时间列")
print("=" * 80)

order_files = list(source_history_dir.glob("order_export*.csv"))
order_files.sort(key=lambda f: f.name)

for f in order_files:
    print(f"\n--- {f.name} ---")
    
    try:
        df_full = pd.read_csv(f, encoding='gbk')
        print(f"  总记录数：{len(df_full)}")
        
        # 检查'开房时间'列
        if '开房时间' in df_full.columns:
            open_times = df_full['开房时间'].dropna()
            print(f"  有效开房时间数：{len(open_times)}")
            
            # 提取日期部分
            dates = []
            for t in open_times:
                t_str = str(t)
                if ' ' in t_str:
                    date_part = t_str.split(' ')[0]
                    dates.append(date_part)
                elif '-' in t_str and len(t_str) > 9:
                    dates.append(t_str[:10])
            
            if dates:
                unique_dates = sorted(list(set(dates)))
                print(f"  文件包含日期：{unique_dates}")
                
                # 统计5月的
                may_dates = [d for d in unique_dates if d.startswith('2026-05')]
                print(f"  5月的日期：{may_dates}")
                
                # 检查午夜场
                if may_dates:
                    print(f"\n  检查午夜场数据（0-5点）：")
                    for d in may_dates:
                        # 筛选出该日期且是0-5点开房的
                        dt_filter = [str(t).startswith(d) and len(str(t)) > 12 and 0 <= int(str(t).split(' ')[1].split(':')[0]) < 6 for t in open_times]
                        midnight_count = sum(dt_filter)
                        if midnight_count > 0:
                            print(f"    {d}: {midnight_count} 单（0-5点）")
        
    except Exception as e:
        print(f"  读取失败：{e}")

print("\n" + "=" * 80)
