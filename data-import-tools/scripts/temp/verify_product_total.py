#!/usr/bin/env python3
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pymysql

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MYSQL_CONFIG

def main():
    print("=" * 80)
    print("验证商品销售数据总金额")
    print("=" * 80)
    
    # 检查汇总表
    summary_path = PROJECT_ROOT / "data" / "source" / "商品销售汇总_2026_04_26.xlsx"
    if summary_path.exists():
        df_summary = pd.read_excel(summary_path)
        total_summary = 0.0
        for _, row in df_summary.iterrows():
            if str(row.get('门店', '')).strip() == '合计':
                continue
            total_summary += float(row.get('销售金额-小计-折后', 0) or 0)
        
        print(f"\n商品销售汇总表总金额: {total_summary:,.2f}元")
        print(f"商品销售汇总表记录数: {len(df_summary) - 1}条")
    
    # 检查明细表
    detail_path = PROJECT_ROOT / "data" / "source" / "商品销售明细_-_商品+包厢维度_2026_04_26.xlsx"
    if detail_path.exists():
        df_detail = pd.read_excel(detail_path)
        total_detail = 0.0
        for _, row in df_detail.iterrows():
            if str(row.get('门店名称', '')).strip() == '合计':
                continue
            total_detail += float(row.get('收入金额', 0) or 0)
        
        print(f"\n商品销售明细表总金额: {total_detail:,.2f}元")
        print(f"商品销售明细表记录数: {len(df_detail) - 1}条")
    
    # 检查数据库
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 查数据库4月25日的总金额
    cursor.execute("""
        SELECT 
            COUNT(*) as record_count,
            SUM(sales_amount) as total_sales
        FROM product_sales
        WHERE data_date = '2026-04-25'
    """)
    db_count, db_total = cursor.fetchone()
    
    print(f"\n数据库中2026-04-25的数据:")
    print(f"  记录数: {db_count}条")
    print(f"  总金额: {db_total:,.2f}元")
    
    # 对比明细表和数据库
    print(f"\n对比明细表和数据库:")
    if detail_path.exists():
        diff_count = abs((len(df_detail) - 1) - db_count)
        diff_amount = abs(total_detail - db_total)
        
        status_count = "✅" if diff_count <= 5 else "❌"
        status_amount = "✅" if diff_amount <= 1 else "❌"
        
        print(f"  记录数差异: {diff_count}条 {status_count}")
        print(f"  金额差异:   {diff_amount:.2f}元 {status_amount}")
        
        if diff_count <= 5 and diff_amount <= 1:
            print(f"\n✅ 商品销售明细表的数据已正确导入到数据库！")
            print(f"   (明细表比汇总表更详细，包含包厢维度)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
