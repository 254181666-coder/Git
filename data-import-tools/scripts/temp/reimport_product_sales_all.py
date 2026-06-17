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

def main():
    print("=" * 80)
    print("重新导入所有商品销售数据")
    print("=" * 80)
    
    source_dir = PROJECT_ROOT / "data" / "source"
    files = sorted(source_dir.glob("商品销售明细*"))
    
    print(f"\n找到 {len(files)} 个文件")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    total_count = 0
    
    for file in files:
        print(f"\n处理文件: {file.name}")
        
        df = pd.read_excel(file)
        df.columns = [c.strip() for c in df.columns]
        
        print(f"  文件行数: {len(df)}")
        
        # 确定日期列
        date_col = None
        if '销售日期::multi-filter' in df.columns:
            date_col = '销售日期::multi-filter'
        elif '销售日期' in df.columns:
            date_col = '销售日期'
        elif '日期' in df.columns:
            date_col = '日期'
        
        if not date_col:
            print(f"  ❌ 未找到日期列")
            continue
        
        # 确定门店列
        store_col = None
        if '门店名称' in df.columns:
            store_col = '门店名称'
        elif '门店' in df.columns:
            store_col = '门店'
        
        if not store_col:
            print(f"  ❌ 未找到门店列")
            continue
        
        # 确定商品列
        product_col = None
        if '商品名称' in df.columns:
            product_col = '商品名称'
        elif '商品名字' in df.columns:
            product_col = '商品名字'
        
        if not product_col:
            print(f"  ❌ 未找到商品列")
            continue
        
        # 确定其他列
        qty_col = '售卖数量' if '售卖数量' in df.columns else '总数量-小计'
        amount_col = '收入金额' if '收入金额' in df.columns else '销售金额-小计-折后'
        category_col = '套餐' if '套餐' in df.columns else '统计类别'
        room_col = '包厢类型::multi-filter' if '包厢类型::multi-filter' in df.columns else '包厢号' if '包厢号' in df.columns else '单位'
        system_category_col = '系统销售类别::multi-filter' if '系统销售类别::multi-filter' in df.columns else '系统销售类别'
        
        # 收集所有日期，先删除旧数据
        all_dates = set()
        for idx, row in df.iterrows():
            try:
                date_val = row[date_col]
                if pd.notna(date_val) and str(date_val).strip() != '':
                    try:
                        dt = pd.to_datetime(date_val)
                        all_dates.add(dt.date())
                    except:
                        pass
            except:
                pass
        
        if not all_dates:
            # 根据文件名推断日期
            match = re.search(r'(\d{4})_(\d{2})_(\d{2})', file.name)
            if match:
                file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                file_date_obj = datetime.strptime(file_date, '%Y-%m-%d').date()
                data_date = file_date_obj - timedelta(days=1)
                all_dates.add(data_date)
                print(f"  根据文件名推断日期: {data_date}")
        
        if all_dates:
            for d in all_dates:
                cursor.execute("DELETE FROM product_sales WHERE data_date = %s", (d,))
            conn.commit()
            print(f"  删除了旧数据: {sorted(all_dates)}")
        
        # 开始导入
        count = 0
        for idx, row in df.iterrows():
            try:
                # 跳过合计行
                if str(row.get(store_col, '')).strip() == '合计' or pd.isna(row.get(product_col, '')) or pd.isna(row.get(store_col, '')):
                    continue
                
                # 获取门店
                store_id = get_store_id(conn, str(row.get(store_col, '')))
                if not store_id:
                    continue
                
                # 获取日期
                data_date = None
                date_val = row.get(date_col, None)
                if pd.notna(date_val) and str(date_val).strip() != '':
                    try:
                        dt = pd.to_datetime(date_val)
                        data_date = dt.date()
                    except:
                        pass
                
                if not data_date:
                    # 从文件名推断
                    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', file.name)
                    if match:
                        file_date = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                        file_date_obj = datetime.strptime(file_date, '%Y-%m-%d').date()
                        data_date = file_date_obj - timedelta(days=1)
                
                if not data_date:
                    continue
                
                # 获取系统分类
                system_cat = str(row.get(system_category_col, '其他')) if system_category_col in df.columns else '其他'
                if system_cat in ['nan', 'None', '']:
                    system_cat = '其他'
                big_category = CATEGORY_MAP.get(system_cat, '其他')
                
                # 插入数据
                cursor.execute("""
                    INSERT INTO product_sales
                    (store_id, data_date, product_name, category, unit_price, quantity, sales_amount, room_type, big_category)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    store_id,
                    data_date,
                    str(row.get(product_col, '')),
                    str(row.get(category_col, '')),
                    float(row.get('单品售价', 0)) if '单品售价' in df.columns and pd.notna(row.get('单品售价')) else 0,
                    int(row.get(qty_col, 0) or 0),
                    float(row.get(amount_col, 0) or 0),
                    str(row.get(room_col, '')),
                    big_category
                ))
                count += 1
            except Exception as e:
                pass
        
        conn.commit()
        total_count += count
        print(f"  ✅ 成功导入 {count} 条")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"完成！总共导入 {total_count} 条")
    print("=" * 80)
    
    # 验证数据
    print("\n验证数据：")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data_date, COUNT(*) as cnt, SUM(sales_amount) as total
        FROM product_sales
        WHERE data_date >= '2026-04-20'
        GROUP BY data_date
        ORDER BY data_date DESC
    """)
    print(f"\n  {'日期':<12} {'记录数':<8} {'销售金额':<12}")
    print("  " + "-" * 32)
    for row in cursor.fetchall():
        print(f"  {row[0]}  {row[1]:>8}  {row[2]:>11.2f}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
