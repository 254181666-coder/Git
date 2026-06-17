
#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=" * 80)
    print("检查归档目录下各个文件的实际数据日期")
    print("=" * 80)
    
    archive_dir = Path(PROJECT_ROOT) / "data" / "archive"
    
    # 检查 source_2026_05_01 目录下的文件
    print("\n📂 检查 source_2026_05_01 目录下的文件:")
    dir_0501 = archive_dir / "source_2026_05_01"
    for f in sorted(dir_0501.glob("*")):
        if f.name.endswith(".xlsx"):
            try:
                df = pd.read_excel(f, nrows=10)
                date_val = None
                for col in ["日期", "销售日期", "销售日期::multi-filter"]:
                    if col in df.columns:
                        try:
                            dates = pd.to_datetime(df[col], errors="coerce").dt.date
                            unique_dates = sorted(dates.dropna().unique())
                            if unique_dates:
                                date_val = unique_dates
                                break
                        except:
                            pass
                print(f"   {f.name}: 数据日期 = {date_val}")
            except Exception as e:
                print(f"   {f.name}: 读取失败 {e}")
    
    # 检查 source_2026_05_02 目录下的文件
    print("\n📂 检查 source_2026_05_02 目录下的文件:")
    dir_0502 = archive_dir / "source_2026_05_02"
    for f in sorted(dir_0502.glob("*")):
        if f.name.endswith(".xlsx"):
            try:
                df = pd.read_excel(f, nrows=10)
                date_val = None
                for col in ["日期", "销售日期", "销售日期::multi-filter"]:
                    if col in df.columns:
                        try:
                            dates = pd.to_datetime(df[col], errors="coerce").dt.date
                            unique_dates = sorted(dates.dropna().unique())
                            if unique_dates:
                                date_val = unique_dates
                                break
                        except:
                            pass
                print(f"   {f.name}: 数据日期 = {date_val}")
            except Exception as e:
                print(f"   {f.name}: 读取失败 {e}")
    
    # 检查 order 相关 csv 文件
    print("\n📂 检查 order_export 相关文件:")
    for f in sorted(archive_dir.glob("**/order_export*.csv")):
        try:
            df = pd.read_csv(f, encoding="gbk", nrows=10)
            if "开房时间" in df.columns:
                dates = pd.to_datetime(df["开房时间"], errors="coerce").dt.date
                unique_dates = sorted(dates.dropna().unique())
                print(f"   {f.parent.name}/{f.name}: 数据日期 = {unique_dates}")
        except Exception as e:
            print(f"   {f.parent.name}/{f.name}: 读取失败 {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

