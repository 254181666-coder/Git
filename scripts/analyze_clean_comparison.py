#!/usr/bin/env python3
"""
通辽店 vs 松原一店 - 数据清洗后的深度对比分析
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.database import query


def get_clean_data(store_id, start_date, end_date):
    """获取清洗后的数据：排除营业外项目"""
    sql = '''
        SELECT 
            product_name,
            big_category,
            SUM(quantity) as total_qty,
            SUM(sales_amount) as total_amt_raw
        FROM product_sales_summary
        WHERE store_id = %s
          AND data_date BETWEEN %s AND %s
          AND product_name NOT LIKE '营业外%%'
        GROUP BY product_name, big_category
    '''
    df = query(sql, (store_id, start_date, end_date))
    if df.empty:
        return df
    df['total_amt'] = df['total_amt_raw'] / 10
    df = df.drop('total_amt_raw', axis=1)
    return df


def analyze_store(store_id, store_name, start_date, end_date):
    """单店分析"""
    print(f'\n{"="*100}')
    print(f'📊 {store_name} 深度分析 ({start_date} 至 {end_date})')
    print(f'{"="*100}')
    
    df = get_clean_data(store_id, start_date, end_date)
    
    if df.empty:
        print(f'{store_name} 没有数据')
        return None
    
    # 1. 总体指标
    total_sku = df['product_name'].nunique()
    total_qty = df['total_qty'].sum()
    total_amt = df['total_amt'].sum()
    
    print(f'\n📌 总体指标')
    print(f'  有效SKU数：{total_sku}')
    print(f'  总销量：{total_qty:,.0f} 件')
    print(f'  总金额：{total_amt:,.2f} 元')
    
    # 2. 按大分类分析
    print(f'\n📌 大分类分析')
    category_df = df.groupby('big_category').agg({
        'product_name': 'nunique',
        'total_qty': 'sum',
        'total_amt': 'sum'
    }).reset_index()
    category_df.columns = ['big_category', 'sku_count', 'total_qty', 'total_amt']
    category_df = category_df.sort_values('total_amt', ascending=False)
    category_df['pct_amt'] = (category_df['total_amt'] / total_amt * 100).round(1)
    
    print(f'  {"大分类":<8} {"SKU":<5} {"销量":>10} {"金额":>12} {"占比":>6}')
    print(f'  {"-"*8} {"-"*5} {"-"*10} {"-"*12} {"-"*6}')
    for _, row in category_df.iterrows():
        print(f'  {row["big_category"]:<8} {row["sku_count"]:>5} {row["total_qty"]:>10,.0f} {row["total_amt"]:>12,.2f} {row["pct_amt"]:>5.1f}%')
    
    # 3. Top 15商品
    print(f'\n📌 Top 15 商品（按销售额）')
    top_products = df.sort_values('total_amt', ascending=False).head(15)
    print(f'  {"排名":<3} {"商品名称":<25} {"销量":>8} {"金额":>12} {"单价":>7}')
    print(f'  {"-"*3} {"-"*25} {"-"*8} {"-"*12} {"-"*7}')
    for rank, (_, row) in enumerate(top_products.iterrows(), 1):
        avg_price = row['total_amt'] / row['total_qty'] if row['total_qty'] > 0 else 0
        print(f'  {rank:<3} {row["product_name"][:25]:<25} {row["total_qty"]:>8,.0f} {row["total_amt"]:>12,.2f} {avg_price:>7.2f}')
    
    # 返回数据用于对比
    return {
        'name': store_name,
        'df': df,
        'category_df': category_df,
        'top_products': top_products,
        'total_sku': total_sku,
        'total_qty': total_qty,
        'total_amt': total_amt
    }


def compare_stores(tongliao, songyuan):
    """两店对比分析"""
    print(f'\n{"="*100}')
    print(f'🔥 两店深度对比分析')
    print(f'{"="*100}')
    
    # 总体对比
    print(f'\n📌 总体指标对比')
    print(f'  {"指标":<15} {"通辽店":>12} {"松原一店":>12} {"差异":>12}')
    print(f'  {"-"*15} {"-"*12} {"-"*12} {"-"*12}')
    print(f'  {"有效SKU数":<15} {tongliao["total_sku"]:>12} {songyuan["total_sku"]:>12} {tongliao["total_sku"]-songyuan["total_sku"]:>+12}')
    print(f'  {"总销量":<15} {tongliao["total_qty"]:>12,.0f} {songyuan["total_qty"]:>12,.0f} {tongliao["total_qty"]-songyuan["total_qty"]:>+12,.0f}')
    print(f'  {"总金额":<15} {tongliao["total_amt"]:>12,.2f} {songyuan["total_amt"]:>12,.2f} {tongliao["total_amt"]-songyuan["total_amt"]:>+12,.2f}')
    
    # 分类对比
    print(f'\n📌 酒水分类对比')
    tl_jiushui = tongliao['category_df'][tongliao['category_df']['big_category'] == '酒水'].iloc[0]
    sy_jiushui = songyuan['category_df'][songyuan['category_df']['big_category'] == '酒水'].iloc[0]
    print(f'  {"指标":<15} {"通辽店":>12} {"松原一店":>12} {"差异":>12}')
    print(f'  {"-"*15} {"-"*12} {"-"*12} {"-"*12}')
    print(f'  {"酒水SKU":<15} {tl_jiushui["sku_count"]:>12} {sy_jiushui["sku_count"]:>12} {tl_jiushui["sku_count"]-sy_jiushui["sku_count"]:>+12}')
    print(f'  {"酒水销量":<15} {tl_jiushui["total_qty"]:>12,.0f} {sy_jiushui["total_qty"]:>12,.0f} {tl_jiushui["total_qty"]-sy_jiushui["total_qty"]:>+12,.0f}')
    print(f'  {"酒水金额":<15} {tl_jiushui["total_amt"]:>12,.2f} {sy_jiushui["total_amt"]:>12,.2f} {tl_jiushui["total_amt"]-sy_jiushui["total_amt"]:>+12,.2f}')
    print(f'  {"酒水占比":<15} {tl_jiushui["pct_amt"]:>10.1f}% {sy_jiushui["pct_amt"]:>10.1f}% {tl_jiushui["pct_amt"]-sy_jiushui["pct_amt"]:>+10.1f}%')
    
    # 找共同商品和独有商品
    tl_products = set(tongliao['df']['product_name'])
    sy_products = set(songyuan['df']['product_name'])
    common_products = tl_products & sy_products
    tl_unique = tl_products - sy_products
    sy_unique = sy_products - tl_products
    
    print(f'\n📌 商品重叠度分析')
    print(f'  共同商品数：{len(common_products)}')
    print(f'  通辽店独有：{len(tl_unique)}')
    print(f'  松原一店独有：{len(sy_unique)}')
    
    # 找通辽卖得好但松原没有的
    print(f'\n📌 通辽店Top 20商品中松原缺失的')
    missing = []
    for _, row in tongliao['top_products'].head(20).iterrows():
        if row['product_name'] not in sy_products:
            missing.append(row)
    if missing:
        print(f'  {"商品名称":<30} {"销量":>8} {"金额":>12}')
        print(f'  {"-"*30} {"-"*8} {"-"*12}')
        for row in missing:
            print(f'  {row["product_name"][:30]:<30} {row["total_qty"]:>8,.0f} {row["total_amt"]:>12,.2f}')
    else:
        print(f'  通辽店Top 20商品松原都有')
    
    # 共同商品对比
    print(f'\n📌 共同商品对比（Top 20）')
    common_df = tongliao['df'][tongliao['df']['product_name'].isin(common_products)].copy()
    common_df = common_df.merge(songyuan['df'][['product_name', 'total_qty', 'total_amt']], 
                                  on='product_name', suffixes=('_tl', '_sy'), how='left')
    common_df = common_df.sort_values('total_amt_tl', ascending=False).head(20)
    
    print(f'  {"商品名称":<25} {"通辽销量":>8} {"通辽金额":>10} {"松原销量":>8} {"松原金额":>10} {"金额差":>10}')
    print(f'  {"-"*25} {"-"*8} {"-"*10} {"-"*8} {"-"*10} {"-"*10}')
    for _, row in common_df.head(20).iterrows():
        amt_diff = row['total_amt_tl'] - row['total_amt_sy']
        print(f'  {row["product_name"][:25]:<25} {row["total_qty_tl"]:>8,.0f} {row["total_amt_tl"]:>10,.0f} {row["total_qty_sy"]:>8,.0f} {row["total_amt_sy"]:>10,.0f} {amt_diff:>+10,.0f}')


def main():
    # 日期范围
    end_date = date(2026, 5, 7)
    start_date = date(2026, 4, 24)
    
    # 单店分析
    tongliao = analyze_store(6, '通辽店', start_date, end_date)
    songyuan = analyze_store(10, '松原一店', start_date, end_date)
    
    # 对比分析
    if tongliao and songyuan:
        compare_stores(tongliao, songyuan)
    
    print(f'\n{"="*100}')
    print(f'✅ 分析完成！')
    print(f'{"="*100}')


if __name__ == '__main__':
    main()

