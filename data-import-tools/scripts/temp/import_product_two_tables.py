#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import pymysql
import re

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG, CATEGORY_MAP
from utils import simplify_store_name

def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

def get_store_id(conn, store_name_raw):
    store_name = simplify_store_name(store_name_raw)
    if not store_name:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM stores WHERE store_name = %s", (store_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO stores (store_name) VALUES (%s)", (store_name,))
    conn.commit()
    return cursor.lastrowid

def import_product_sales_summary(conn, file_path):
    """导入商品销售汇总表"""
    print(f"\n  导入汇总表: {file_path.name}")
    
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    
    # 确定日期列
    date_col = None
    if "日期" in df.columns:
        date_col = "日期"
    elif "销售日期" in df.columns:
        date_col = "销售日期"
    elif "销售日期::multi-filter" in df.columns:
        date_col = "销售日期::multi-filter"
    
    # 收集所有日期，先删除旧数据
    all_dates = set()
    for _, row in df.iterrows():
        try:
            if pd.isna(row.get("门店")) or str(row.get("门店")).strip() == "合计":
                continue
            
            if date_col:
                date_str = str(row.get(date_col, ""))
                if "~" in date_str:
                    ds_part = date_str.split("~")[0]
                    if len(ds_part) == 8:
                        ds = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
                        all_dates.add(ds)
                elif pd.notna(row.get(date_col)):
                    try:
                        dt = pd.to_datetime(row.get(date_col))
                        ds = dt.strftime("%Y-%m-%d")
                        all_dates.add(ds)
                    except:
                        pass
        except:
            pass
    
    # 从文件名推断日期
    if not all_dates:
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
        if match:
            file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
            data_date = file_date_obj - timedelta(days=1)
            all_dates.add(data_date.strftime("%Y-%m-%d"))
    
    # 删除旧数据
    if all_dates:
        cursor = conn.cursor()
        for ds in all_dates:
            cursor.execute("DELETE FROM product_sales_summary WHERE data_date = %s", (ds,))
        conn.commit()
        print(f"  删除了旧数据: {sorted(all_dates)}")
    
    count = 0
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            # 跳过合计行
            if pd.isna(row.get("门店")) or pd.isna(row.get("商品名字")):
                continue
            if str(row.get("门店")).strip() == "合计" or str(row.get("商品名字")).strip() == "合计":
                continue
            
            # 获取门店ID
            store_id = get_store_id(conn, str(row.get("门店", "")))
            if not store_id:
                continue
            
            # 获取日期
            data_date = None
            if date_col:
                date_str = str(row.get(date_col, ""))
                if "~" in date_str:
                    ds_part = date_str.split("~")[0]
                    if len(ds_part) == 8:
                        data_date = f"{ds_part[:4]}-{ds_part[4:6]}-{ds_part[6:8]}"
                elif pd.notna(row.get(date_col)):
                    try:
                        dt = pd.to_datetime(row.get(date_col))
                        data_date = dt.strftime("%Y-%m-%d")
                    except:
                        pass
            
            # 从文件名推断日期
            if not data_date:
                match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
                if match:
                    file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                    data_date = (file_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            
            if not data_date:
                continue
            
            # 获取系统分类并映射big_category
            system_category = str(row.get("系统销售类别::multi-filter", "其他"))
            if system_category in ["nan", "None", ""]:
                system_category = "其他"
            big_category = CATEGORY_MAP.get(system_category, "其他")
            
            # 插入数据
            cursor.execute("""
                INSERT INTO product_sales_summary
                (store_id, data_date, product_name, product_code, category, system_category, unit, unit_price, quantity, sales_amount, big_category)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                store_id,
                data_date,
                str(row.get("商品名字", "")),
                str(row.get("商品编码", "")),
                str(row.get("统计类别", "")),
                system_category,
                str(row.get("单位", "")),
                float(row.get("单品售价", 0) or 0),
                int(row.get("销售数量-小计", 0) or 0),
                float(row.get("销售金额-小计-折后", 0) or 0),
                big_category
            ))
            count += 1
        except Exception as e:
            # print(f"错误: {e}")
            pass
    
    conn.commit()
    print(f"  ✅ 导入了 {count} 条记录")
    return count

def import_product_sales_detail(conn, file_path):
    """导入商品销售明细表"""
    print(f"\n  导入明细表: {file_path.name}")
    
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    
    # 确定日期列
    date_col = None
    if "日期" in df.columns:
        date_col = "日期"
    elif "销售日期" in df.columns:
        date_col = "销售日期"
    elif "销售日期::multi-filter" in df.columns:
        date_col = "销售日期::multi-filter"
    
    # 收集所有日期，先删除旧数据
    all_dates = set()
    for _, row in df.iterrows():
        try:
            if pd.isna(row.get("门店名称")) or str(row.get("门店名称")).strip() == "合计":
                continue
            
            if date_col:
                date_str = str(row.get(date_col, ""))
                if pd.notna(row.get(date_col)):
                    try:
                        dt = pd.to_datetime(row.get(date_col))
                        ds = dt.strftime("%Y-%m-%d")
                        all_dates.add(ds)
                    except:
                        pass
        except:
            pass
    
    # 从文件名推断日期
    if not all_dates:
        match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
        if match:
            file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
            data_date = file_date_obj - timedelta(days=1)
            all_dates.add(data_date.strftime("%Y-%m-%d"))
    
    # 删除旧数据
    if all_dates:
        cursor = conn.cursor()
        for ds in all_dates:
            cursor.execute("DELETE FROM product_sales_detail WHERE data_date = %s", (ds,))
        conn.commit()
        print(f"  删除了旧数据: {sorted(all_dates)}")
    
    count = 0
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            # 跳过合计行
            if pd.isna(row.get("门店名称")) or pd.isna(row.get("商品名称")):
                continue
            if str(row.get("门店名称")).strip() == "合计" or str(row.get("商品名称")).strip() == "合计":
                continue
            
            # 获取门店ID
            store_id = get_store_id(conn, str(row.get("门店名称", "")))
            if not store_id:
                continue
            
            # 获取日期
            data_date = None
            if date_col:
                date_str = str(row.get(date_col, ""))
                if pd.notna(row.get(date_col)):
                    try:
                        dt = pd.to_datetime(row.get(date_col))
                        data_date = dt.strftime("%Y-%m-%d")
                    except:
                        pass
            
            # 从文件名推断日期
            if not data_date:
                match = re.search(r"(\d{4})_(\d{2})_(\d{2})", file_path.name)
                if match:
                    file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    file_date_obj = datetime.strptime(file_date, "%Y-%m-%d").date()
                    data_date = (file_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            
            if not data_date:
                continue
            
            # 插入数据
            cursor.execute("""
                INSERT INTO product_sales_detail
                (store_id, data_date, product_name, product_code, package, room_no, room_type, quantity, sales_amount, order_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                store_id,
                data_date,
                str(row.get("商品名称", "")),
                str(row.get("商品编码", "")),
                str(row.get("套餐", "")),
                str(row.get("包厢号", "")),
                str(row.get("包厢类型::multi-filter", "")),
                int(row.get("售卖数量", 0) or 0),
                float(row.get("收入金额", 0) or 0),
                str(row.get("订单类型", "")),
            ))
            count += 1
        except Exception as e:
            # print(f"错误: {e}")
            pass
    
    conn.commit()
    print(f"  ✅ 导入了 {count} 条记录")
    return count

def main():
    print("=" * 80)
    print("导入商品销售数据到两个新表")
    print("=" * 80)
    
    conn = get_conn()
    
    # 先从archive目录复制文件到source目录
    print("\n1. 从archive目录复制商品销售汇总表...")
    archive_dir = PROJECT_ROOT / "data" / "archive"
    source_dir = PROJECT_ROOT / "data" / "source"
    source_dir.mkdir(exist_ok=True)
    
    for day_dir in sorted(archive_dir.glob("source_2026_04_*")):
        if not day_dir.is_dir():
            continue
        for f in day_dir.glob("商品销售汇总*.xlsx"):
            dest = source_dir / f.name
            if not dest.exists():
                import shutil
                shutil.copy(f, dest)
                print(f"  复制: {f.name}")
    
    for day_dir in sorted(archive_dir.glob("source_2026_04_*")):
        if not day_dir.is_dir():
            continue
        for f in day_dir.glob("商品销售明细*.xlsx"):
            dest = source_dir / f.name
            if not dest.exists():
                import shutil
                shutil.copy(f, dest)
                print(f"  复制: {f.name}")
    
    # 2. 导入商品销售汇总表
    print("\n2. 导入商品销售汇总表到 product_sales_summary...")
    summary_files = sorted(source_dir.glob("商品销售汇总*.xlsx"))
    total_summary_count = 0
    for f in summary_files:
        cnt = import_product_sales_summary(conn, f)
        total_summary_count += cnt
    print(f"\n汇总表总共导入了: {total_summary_count} 条")
    
    # 3. 导入商品销售明细表
    print("\n3. 导入商品销售明细表到 product_sales_detail...")
    detail_files = sorted(source_dir.glob("商品销售明细*.xlsx"))
    total_detail_count = 0
    for f in detail_files:
        cnt = import_product_sales_detail(conn, f)
        total_detail_count += cnt
    print(f"\n明细表总共导入了: {total_detail_count} 条")
    
    # 4. 验证数据
    print("\n" + "=" * 80)
    print("验证数据")
    print("=" * 80)
    
    cursor = conn.cursor()
    print("\nproduct_sales_summary 表:")
    cursor.execute("""
        SELECT data_date, COUNT(*) as cnt, SUM(sales_amount) as total
        FROM product_sales_summary
        WHERE data_date >= '2026-04-20'
        GROUP BY data_date
        ORDER BY data_date DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条, {row[2]:.2f} 元")
    
    cursor.execute("""
        SELECT big_category, COUNT(*) as cnt, SUM(sales_amount) as total
        FROM product_sales_summary
        WHERE data_date = '2026-04-25'
        GROUP BY big_category
        ORDER BY total DESC
    """)
    print("\n2026-04-25 的 big_category 分布:")
    for row in cursor.fetchall():
        print(f"  {row[0] or '其他'}: {row[1]} 条, {row[2]:.2f} 元")
    
    print("\nproduct_sales_detail 表:")
    cursor.execute("""
        SELECT data_date, COUNT(*) as cnt, SUM(sales_amount) as total
        FROM product_sales_detail
        WHERE data_date >= '2026-04-20'
        GROUP BY data_date
        ORDER BY data_date DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条, {row[2]:.2f} 元")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 导入完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
