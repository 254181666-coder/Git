#!/usr/bin/env python3
"""
通辽店 vs 松原一店 - 人效深度分析（储值提成 + 商品提成）
"""
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.database import query


def get_stored_commission(store_id, start_date, end_date):
    """获取储值提成数据"""
    sql = '''
        SELECT 
            business_date,
            commission_staff,
            staff_account,
            stored_amount,
            commission_amount,
            commission_rule
        FROM stored_commission
        WHERE store_id = %s
          AND business_date BETWEEN %s AND %s
    '''
    df = query(sql, (store_id, start_date, end_date))
    return df


def get_product_commission(store_id, start_date, end_date):
    """获取商品提成数据"""
    sql = '''
        SELECT 
            business_date,
            commission_staff,
            staff_account,
            product,
            quantity,
            paid_amount,
            commission_amount
        FROM product_commission
        WHERE store_id = %s
          AND business_date BETWEEN %s AND %s
    '''
    df = query(sql, (store_id, start_date, end_date))
    return df


def analyze_personnel(store_id, store_name, start_date, end_date):
    """人员分析"""
    print(f'\n{"="*100}')
    print(f'👥 {store_name} 人员分析 ({start_date} 至 {end_date})')
    print(f'{"="*100}')
    
    # 获取数据
    stored_df = get_stored_commission(store_id, start_date, end_date)
    product_df = get_product_commission(store_id, start_date, end_date)
    
    # 1. 储值提成分析
    print(f'\n📌 1. 储值提成分析')
    if stored_df.empty:
        print(f'  无储值提成数据')
    else:
        stored_by_staff = stored_df.groupby('commission_staff').agg({
            'stored_amount': 'sum',
            'commission_amount': 'sum',
            'business_date': 'count'
        }).reset_index()
        stored_by_staff.columns = ['员工', '储值金额', '储值提成', '储值笔数']
        stored_by_staff = stored_by_staff.sort_values('储值提成', ascending=False)
        
        total_stored_amt = stored_by_staff['储值金额'].sum()
        total_stored_commission = stored_by_staff['储值提成'].sum()
        total_stored_trans = stored_by_staff['储值笔数'].sum()
        stored_staff_count = stored_by_staff['员工'].nunique()
        
        print(f'  储值总金额：{total_stored_amt:,.2f} 元')
        print(f'  储值总提成：{total_stored_commission:,.2f} 元')
        print(f'  储值总笔数：{total_stored_trans:,} 笔')
        print(f'  参与储值员工：{stored_staff_count} 人')
        
        print(f'\n  储值员工Top 10：')
        print(f'  {"排名":<4} {"员工":<12} {"储值金额":>12} {"储值提成":>12} {"储值笔数":>10} {"平均每笔":>10}')
        print(f'  {"-"*4} {"-"*12} {"-"*12} {"-"*12} {"-"*10} {"-"*10}')
        for rank, (_, row) in enumerate(stored_by_staff.head(10).iterrows(), 1):
            avg_per_trans = row['储值提成'] / row['储值笔数'] if row['储值笔数'] > 0 else 0
            print(f'  {rank:<4} {row["员工"][:12]:<12} {row["储值金额"]:>12,.2f} {row["储值提成"]:>12,.2f} {row["储值笔数"]:>10} {avg_per_trans:>10.2f}')
    
    # 2. 商品提成分析
    print(f'\n📌 2. 商品提成分析')
    if product_df.empty:
        print(f'  无商品提成数据')
    else:
        product_by_staff = product_df.groupby('commission_staff').agg({
            'quantity': 'sum',
            'paid_amount': 'sum',
            'commission_amount': 'sum',
            'business_date': 'count'
        }).reset_index()
        product_by_staff.columns = ['员工', '商品销量', '商品销售金额', '商品提成', '商品笔数']
        product_by_staff = product_by_staff.sort_values('商品提成', ascending=False)
        
        total_product_qty = product_by_staff['商品销量'].sum()
        total_product_amt = product_by_staff['商品销售金额'].sum() / 10  # 转为元
        total_product_commission = product_by_staff['商品提成'].sum()
        total_product_trans = product_by_staff['商品笔数'].sum()
        product_staff_count = product_by_staff['员工'].nunique()
        
        print(f'  商品总销量：{total_product_qty:,.0f} 件')
        print(f'  商品总金额：{total_product_amt:,.2f} 元')
        print(f'  商品总提成：{total_product_commission:,.2f} 元')
        print(f'  商品总笔数：{total_product_trans:,} 笔')
        print(f'  参与商品提成员工：{product_staff_count} 人')
        
        print(f'\n  商品提成员工Top 10：')
        print(f'  {"排名":<4} {"员工":<12} {"商品金额":>12} {"商品提成":>12} {"商品笔数":>10} {"平均每笔":>10}')
        print(f'  {"-"*4} {"-"*12} {"-"*12} {"-"*12} {"-"*10} {"-"*10}')
        for rank, (_, row) in enumerate(product_by_staff.head(10).iterrows(), 1):
            avg_per_trans = row['商品提成'] / row['商品笔数'] if row['商品笔数'] > 0 else 0
            print(f'  {rank:<4} {row["员工"][:12]:<12} {row["商品销售金额"]/10:>12,.2f} {row["商品提成"]:>12,.2f} {row["商品笔数"]:>10} {avg_per_trans:>10.2f}')
        
        # 商品提成Top商品
        print(f'\n  商品提成Top 20商品：')
        top_products = product_df.groupby('product').agg({
            'quantity': 'sum',
            'commission_amount': 'sum'
        }).reset_index()
        top_products.columns = ['商品', '销量', '提成金额']
        top_products = top_products.sort_values('提成金额', ascending=False).head(20)
        print(f'  {"排名":<4} {"商品":<25} {"销量":>10} {"提成":>10}')
        print(f'  {"-"*4} {"-"*25} {"-"*10} {"-"*10}')
        for rank, (_, row) in enumerate(top_products.iterrows(), 1):
            print(f'  {rank:<4} {row["商品"][:25]:<25} {row["销量"]:>10,.0f} {row["提成金额"]:>10,.2f}')
    
    # 3. 综合分析
    print(f'\n📌 3. 综合人效分析')
    
    # 合并两种提成
    all_staff = set()
    if not stored_df.empty:
        all_staff.update(stored_df['commission_staff'].unique())
    if not product_df.empty:
        all_staff.update(product_df['commission_staff'].unique())
    
    summary = []
    for staff in all_staff:
        stored = stored_df[stored_df['commission_staff'] == staff] if not stored_df.empty else pd.DataFrame()
        product = product_df[product_df['commission_staff'] == staff] if not product_df.empty else pd.DataFrame()
        
        summary.append({
            '员工': staff,
            '储值金额': stored['stored_amount'].sum() if not stored.empty else 0,
            '储值提成': stored['commission_amount'].sum() if not stored.empty else 0,
            '储值笔数': len(stored) if not stored.empty else 0,
            '商品金额': product['paid_amount'].sum() / 10 if not product.empty else 0,
            '商品提成': product['commission_amount'].sum() if not product.empty else 0,
            '商品笔数': len(product) if not product.empty else 0
        })
    
    summary_df = pd.DataFrame(summary)
    summary_df['总提成'] = summary_df['储值提成'] + summary_df['商品提成']
    summary_df = summary_df.sort_values('总提成', ascending=False)
    
    total_all_commission = summary_df['总提成'].sum()
    total_all_staff = len(summary_df)
    
    print(f'  总参与员工：{total_all_staff} 人')
    print(f'  总提成金额：{total_all_commission:,.2f} 元')
    
    print(f'\n  综合提成员工Top 10：')
    print(f'  {"排名":<4} {"员工":<12} {"储值提成":>10} {"商品提成":>10} {"总提成":>12} {"总笔数":>10}')
    print(f'  {"-"*4} {"-"*12} {"-"*10} {"-"*10} {"-"*12} {"-"*10}')
    for rank, (_, row) in enumerate(summary_df.head(10).iterrows(), 1):
        total_trans = row['储值笔数'] + row['商品笔数']
        print(f'  {rank:<4} {row["员工"][:12]:<12} {row["储值提成"]:>10,.2f} {row["商品提成"]:>10,.2f} {row["总提成"]:>12,.2f} {total_trans:>10}')
    
    # 提成分布分析
    print(f'\n📌 4. 提成分布分析（全部员工）：')
    if len(summary_df) > 0:
        percentiles = [0.1, 0.25, 0.5, 0.75, 0.9]
        print(f'  前10%员工：{summary_df["总提成"].quantile(0.9):,.2f} 元')
        print(f'  前25%员工：{summary_df["总提成"].quantile(0.75):,.2f} 元')
        print(f'  中位数：{summary_df["总提成"].quantile(0.5):,.2f} 元')
        print(f'  后25%员工：{summary_df["总提成"].quantile(0.25):,.2f} 元')
        
        # 头部贡献
        top_3_pct = summary_df['总提成'].head(3).sum() / total_all_commission * 100
        top_5_pct = summary_df['总提成'].head(5).sum() / total_all_commission * 100
        print(f'  前3名贡献：{top_3_pct:.1f}%')
        print(f'  前5名贡献：{top_5_pct:.1f}%')
    
    return {
        'name': store_name,
        'stored_df': stored_df,
        'product_df': product_df,
        'summary_df': summary_df
    }


def compare_personnel(tongliao, songyuan):
    """两店人员对比"""
    print(f'\n{"="*100}')
    print(f'🔥 两店人效对比分析')
    print(f'{"="*100}')
    
    print(f'\n📌 总体指标对比')
    
    tl_summary = tongliao['summary_df']
    sy_summary = songyuan['summary_df']
    
    tl_total_staff = len(tl_summary)
    tl_total_commission = tl_summary['总提成'].sum()
    tl_avg_commission = tl_total_commission / tl_total_staff
    
    sy_total_staff = len(sy_summary)
    sy_total_commission = sy_summary['总提成'].sum()
    sy_avg_commission = sy_total_commission / sy_total_staff
    
    print(f'  {"指标":<20} {"通辽店":>12} {"松原一店":>12} {"差异":>12}')
    print(f'  {"-"*20} {"-"*12} {"-"*12} {"-"*12}')
    print(f'  {"总员工数":<20} {tl_total_staff:>12} {sy_total_staff:>12} {tl_total_staff-sy_total_staff:>+12}')
    print(f'  {"总提成":<20} {tl_total_commission:>12,.2f} {sy_total_commission:>12,.2f} {tl_total_commission-sy_total_commission:>+12,.2f}')
    print(f'  {"人均提成":<20} {tl_avg_commission:>12,.2f} {sy_avg_commission:>12,.2f} {tl_avg_commission-sy_avg_commission:>+12,.2f}')
    
    # 提成分布对比
    print(f'\n📌 提成分布对比：')
    print(f'  {"分位":<10} {"通辽店":>12} {"松原一店":>12}')
    print(f'  {"-"*10} {"-"*12} {"-"*12}')
    for p in [0.1, 0.25, 0.5, 0.75, 0.9]:
        tl_p = tl_summary['总提成'].quantile(p)
        sy_p = sy_summary['总提成'].quantile(p)
        print(f'  {int(p*100)}%分位 {tl_p:>12,.2f} {sy_p:>12,.2f}')
    
    # 头部贡献对比
    print(f'\n📌 头部贡献对比：')
    tl_top3 = tl_summary['总提成'].head(3).sum() / tl_total_commission * 100
    tl_top5 = tl_summary['总提成'].head(5).sum() / tl_total_commission * 100
    sy_top3 = sy_summary['总提成'].head(3).sum() / sy_total_commission * 100
    sy_top5 = sy_summary['总提成'].head(5).sum() / sy_total_commission * 100
    print(f'  {"指标":<15} {"通辽店":>10} {"松原一店":>10}')
    print(f'  {"-"*15} {"-"*10} {"-"*10}')
    print(f'  前3名贡献 {tl_top3:>8.1f}% {sy_top3:>8.1f}%')
    print(f'  前5名贡献 {tl_top5:>8.1f}% {sy_top5:>8.1f}%')


def main():
    # 日期范围
    end_date = date(2026, 5, 7)
    start_date = date(2026, 4, 24)
    
    # 单店分析
    tongliao = analyze_personnel(6, '通辽店', start_date, end_date)
    songyuan = analyze_personnel(10, '松原一店', start_date, end_date)
    
    # 对比分析
    compare_personnel(tongliao, songyuan)
    
    print(f'\n{"="*100}')
    print(f'✅ 人效分析完成！')
    print(f'{"="*100}')


if __name__ == '__main__':
    main()

