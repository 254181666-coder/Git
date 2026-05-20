#!/usr/bin/env python3
"""
轻舟日报分析脚本（改进版）
生成储值率分析图和收入分析综合图

改进内容：
1. 使用「会员卡号」计数充值次数
2. 使用「酒水变动本金」作为储值金额
3. 最终以日营业数据的「储值卡销售」为准
4. 显示数据对比和差额

项目结构：
- 数据源：共享 Manpower/data/source
- 输出：轻舟日报分析/data/output
- 归档：轻舟日报分析/data/archive
"""

import pandas as pd
from datetime import datetime, timedelta
from matplotlib.gridspec import GridSpec
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 共享数据源目录
# 数据源目录
SOURCE_DIR = '/Users/ann/Desktop/AI/Project/Manpower/data/source'
# 独立输出目录
OUTPUT_DIR = '/Users/ann/Desktop/AI/Project/每日报告/data/output'
# 独立归档目录
ARCHIVE_DIR_QINGZHOU = '/Users/ann/Desktop/AI/Project/每日报告/data/archive'

def remove_excluded_stores(df, store_column='门店'):
    df = df[df[store_column] != '总部']
    df = df[~df[store_column].str.contains('临河街', na=False)]
    return df

def find_store_file():
    for f in os.listdir(SOURCE_DIR):
        if not f.startswith('.') and '日营业数据' in f and f.endswith('.xlsx'):
            return os.path.join(SOURCE_DIR, f)
    return None

def find_recharge_file():
    for f in os.listdir(SOURCE_DIR):
        if not f.startswith('.') and '储值订单表' in f and f.endswith('.xlsx'):
            return os.path.join(SOURCE_DIR, f)
    return None

def generate_charts():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    weekday = (datetime.now() - timedelta(days=1)).weekday()
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    date_str = f"{yesterday} {weekdays[weekday]}"
    
    store_file = find_store_file()
    if not store_file:
        print("未找到日营业数据文件")
        return

    recharge_file = find_recharge_file()
    if not recharge_file:
        print("未找到储值订单文件")
        return

    print(f"使用数据文件:")
    print(f"  日营业数据: {store_file}")
    print(f"  储值订单: {recharge_file}")

    # 读取日营业数据
    store_df = pd.read_excel(store_file)
    store_df = store_df[store_df['门店'] != '总部']
    store_df['门店'] = store_df['门店'].str.replace('私人订制KTV', '').str.replace('糖果华庭KTV', '')
    store_df = remove_excluded_stores(store_df)

    # 读取包房数
    room_df = pd.read_excel(f'{OUTPUT_DIR}/包房数.xlsx')
    room_df.columns = ['门店', '包房数']

    # 门店名称统一：去掉所有"店"字，保持一致
    store_df['门店'] = store_df['门店'].str.replace('店$', '', regex=True)
    room_df['门店'] = room_df['门店'].str.replace('店$', '', regex=True)
    
    name_map = {'江南秀': '松原一', '斯堡特': '松原二'}
    store_df['门店'] = store_df['门店'].replace(name_map)
    room_df['门店'] = room_df['门店'].replace(name_map)

    # 合并数据
    store_df = pd.merge(store_df, room_df, on='门店', how='left')
    store_df['空包率'] = (1 - store_df['晚场待客最高峰台数'] / store_df['包房数']) * 100
    store_df['空包率'] = store_df['空包率'].clip(lower=0)
    store_df['空包率'] = store_df['空包率'].round(1)
    store_df['空包率'] = store_df['空包率'].apply(lambda x: f'{x:.1f}%')

    # 读取储值数据
    recharge_df = pd.read_excel(recharge_file)
    recharge_df['小时'] = pd.to_datetime(recharge_df['充值时间']).dt.hour
    recharge_df['充值门店'] = recharge_df['充值门店'].str.replace('私人订制KTV', '').str.replace('糖果华庭KTV', '')
    recharge_df = recharge_df.dropna(subset=['充值门店'])  # 先删除NaN
    recharge_df = remove_excluded_stores(recharge_df, '充值门店')
    recharge_df['充值门店'] = recharge_df['充值门店'].str.replace('店$', '', regex=True)  # 去掉"店"字

    recharge_df['18点前储值'] = recharge_df.apply(lambda r: 1 if 8 <= r['小时'] < 18 else 0, axis=1)
    recharge_df['18点-24点储值'] = recharge_df.apply(lambda r: 1 if 18 <= r['小时'] < 24 else 0, axis=1)
    recharge_df['00点后储值'] = recharge_df.apply(lambda r: 1 if 0 <= r['小时'] <= 7 else 0, axis=1)

    # 使用「会员卡号」计数充值次数，使用「酒水变动本金」作为储值金额
    recharge_agg = recharge_df.groupby('充值门店').agg({
        '会员卡号': 'count',  # 用会员卡号计数充值次数
        '酒水变动本金': 'sum',  # 用酒水变动本金作为储值金额
        '18点前储值': 'sum',
        '18点-24点储值': 'sum',
        '00点后储值': 'sum'
    }).reset_index()
    recharge_agg.columns = ['门店', '总储值次数', '充值总金额', '18点前储值', '18点-24点储值', '00点后储值']

    # 合并储值数据
    merged = pd.merge(store_df[['门店', '全天待客台数', '18点前待客', '18点-24点待客', '00点后待客', '储值卡销售']],
                      recharge_agg,
                      on='门店', how='left')
    merged = merged.fillna(0)
    
    # 最终以日营业数据的「储值卡销售」为准！
    print("\n📊 数据对比（储值金额）：")
    print("-" * 80)
    for _, row in merged.iterrows():
        if row['储值卡销售'] > 0:
            diff = row['储值卡销售'] - row['充值总金额']
            print(f"  {row['门店']:12} | 日营业数据: {row['储值卡销售']:>10.0f} | 储值订单: {row['充值总金额']:>10.0f} | 差额: {diff:>+10.0f}")
    
    # 用日营业数据的「储值卡销售」覆盖「充值总金额」
    merged['充值总金额'] = merged['储值卡销售']
    
    print("-" * 80)
    print("✅ 已使用日营业数据的「储值卡销售」作为最终储值金额！\n")
    
    for col in ['全天待客台数', '18点前待客', '18点-24点待客', '00点后待客', '总储值次数', '充值总金额', '18点前储值', '18点-24点储值', '00点后储值']:
        if merged[col].dtype == 'float64':
            merged[col] = merged[col].astype(int)

    # 读取次卡数据
    card_file = None
    for f in os.listdir(SOURCE_DIR):
        if not f.startswith('.') and 'card' in f.lower() and f.endswith('.csv'):
            card_file = os.path.join(SOURCE_DIR, f)
            break
    
    if card_file:
        card_df = pd.read_csv(card_file, encoding='gbk')
        card_df = card_df[card_df['变动类型'] == '卡券活动发放']
        card_df['发放门店'] = card_df['发放门店'].str.replace('私人订制KTV', '').str.replace('糖果华庭KTV', '')
        card_df['发放门店'] = card_df['发放门店'].str.replace('店$', '', regex=True)
        card_counts = card_df.groupby('发放门店').size().reset_index(name='次卡总数')
        card_counts.columns = ['门店', '次卡总数']
        merged = pd.merge(merged, card_counts, on='门店', how='left')
        merged['次卡总数'] = merged['次卡总数'].fillna(0).astype(int)
    else:
        merged['次卡总数'] = 0

    # 计算储值率
    merged['18点前储值率'] = (merged['18点前储值'] / merged['18点前待客'] * 100).round(1).replace(float('inf'), 0)
    merged['18点-24点储值率'] = (merged['18点-24点储值'] / merged['18点-24点待客'] * 100).round(1).replace(float('inf'), 0)
    merged['00点后储值率'] = (merged['00点后储值'] / merged['00点后待客'] * 100).round(1).replace(float('inf'), 0)
    merged = merged.sort_values('全天待客台数', ascending=False)

    # ========== 生成储值率分析图 ==========
    CHART_FILE = f'{OUTPUT_DIR}/{yesterday}储值率分析图.png'
    fig = plt.figure(figsize=(16, 10))

    gs = GridSpec(2, 1, figure=fig, height_ratios=[2, 1])
    ax_chart = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])

    x = range(len(merged))
    width = 0.25
    stores = merged['门店'].tolist()

    bars1 = ax_chart.bar([i - width for i in x], merged['18点前储值率'].fillna(0), width, label='18点前储值率', color='#FF4136')
    bars2 = ax_chart.bar(x, merged['18点-24点储值率'].fillna(0), width, label='18点-24点储值率', color='#FFDC00')
    bars3 = ax_chart.bar([i + width for i in x], merged['00点后储值率'].fillna(0), width, label='00点后储值率', color='#0074D9')

    ax_chart.set_xlabel('门店', fontsize=12)
    ax_chart.set_ylabel('储值率 (%)', fontsize=12)
    ax_chart.set_title(f'各门店不同时段储值率分析 (日期: {date_str})', fontsize=14, fontweight='bold')
    ax_chart.set_xticks(x)
    ax_chart.set_xticklabels(stores, rotation=45, ha='right', fontsize=9)
    ax_chart.legend(loc='upper right', fontsize=10)
    max_rate = merged[['18点前储值率', '18点-24点储值率', '00点后储值率']].max().max()
    ax_chart.set_ylim(0, max_rate * 1.2 if max_rate > 0 else 100)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax_chart.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=7)

    ax_table.axis('off')
    summary_cols = ['门店', '全天待客台数', '总储值次数', '充值总金额', '次卡总数',
                    '18点前待客', '18点前储值', '18点前储值率',
                    '18点-24点待客', '18点-24点储值', '18点-24点储值率',
                    '00点后待客', '00点后储值', '00点后储值率']
    display_df = merged[summary_cols].copy()
    display_df['充值总金额'] = display_df['充值总金额'].apply(lambda x: round(x/10, 1) if pd.notna(x) else x)
    table_data = display_df.values.tolist()
    table = ax_table.table(cellText=table_data, colLabels=summary_cols, loc='upper center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.3)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#404040')
            cell.set_text_props(color='white', fontweight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#F5F5F5')
    ax_table.set_title('储值卡汇总数据表', fontsize=12, fontweight='bold', pad=25)

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=150, bbox_inches='tight', facecolor='white')
    
    archive_file = f'{ARCHIVE_DIR_QINGZHOU}/{yesterday}储值率分析图.png'
    plt.savefig(archive_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ 储值率分析图已保存: {CHART_FILE}")
    plt.close()

    # ========== 生成收入分析综合图 ==========
    revenue_df = store_df.copy()
    revenue_df['其他收入'] = revenue_df['总计营业额'] - revenue_df['储值卡销售'] - revenue_df['线上团购应收']
    revenue_df = revenue_df[revenue_df['总计营业额'] > 0]
    revenue_df['其他收入'] = revenue_df['其他收入'].round(2)
    revenue_df_for_chart = revenue_df[['门店', '总计营业额', '储值卡销售', '线上团购应收', '其他收入', '空包率']].sort_values('总计营业额', ascending=False).reset_index(drop=True)

    stores = revenue_df_for_chart['门店'].tolist()
    stored_vals = [v/10 for v in revenue_df_for_chart['储值卡销售'].tolist()]
    online_vals = [v/10 for v in revenue_df_for_chart['线上团购应收'].tolist()]
    other_vals = [v/10 for v in revenue_df_for_chart['其他收入'].tolist()]
    totals = [v/10 for v in revenue_df_for_chart['总计营业额'].tolist()]
    vacancy_rates = revenue_df_for_chart['空包率'].tolist()

    REVENUE_CHART = f'{OUTPUT_DIR}/收入分析综合图_{yesterday}.png'
    fig = plt.figure(figsize=(20, 12))

    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.5, 1, 1], height_ratios=[1.5, 1])

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_pie = fig.add_subplot(gs[0, 1])
    ax_table = fig.add_subplot(gs[0, 2])
    ax_line = fig.add_subplot(gs[1, :])

    x = range(len(revenue_df_for_chart))
    width = 0.65

    ax_bar.bar(x, stored_vals, width, label='储值卡销售', color='#FF4136')
    ax_bar.bar(x, online_vals, width, bottom=stored_vals, label='线上团购应收', color='#FFDC00')
    ax_bar.bar(x, other_vals, width, bottom=[s+o for s,o in zip(stored_vals, online_vals)], label='其他收入', color='#0074D9')

    ax_bar.set_xlabel('门店', fontsize=12)
    ax_bar.set_ylabel('金额 (元)', fontsize=12)
    ax_bar.set_title('各门店收入结构堆积图', fontsize=14, fontweight='bold')
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(stores, rotation=45, ha='right', fontsize=9)
    ax_bar.legend(loc='upper right', fontsize=9)

    for i, (sv, ov, ot, tot) in enumerate(zip(stored_vals, online_vals, other_vals, totals)):
        ax_bar.text(i, tot + 300, f'{tot:,.0f}', ha='center', va='bottom', fontsize=8, color='black')
        if sv > 0:
            pct = sv/tot*100
            ax_bar.text(i, sv/2, f'{pct:.0f}%', ha='center', va='center', fontsize=7, color='black', fontweight='bold')
        if ov > 0:
            pct = ov/tot*100
            ax_bar.text(i, sv + ov/2, f'{pct:.0f}%', ha='center', va='center', fontsize=7, color='black', fontweight='bold')
        if ot > 0:
            pct = ot/tot*100
            ax_bar.text(i, sv + ov + ot/2, f'{pct:.0f}%', ha='center', va='center', fontsize=7, color='black', fontweight='bold')

    # 饼图 - 最高门店
    top_store = revenue_df_for_chart.iloc[0]
    pie_data = [top_store['储值卡销售'], top_store['线上团购应收'], top_store['其他收入']]
    pie_labels = ['储值卡销售', '线上团购应收', '其他收入']
    pie_colors = ['#FF4136', '#FFDC00', '#0074D9']
    ax_pie.pie(pie_data, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%', startangle=90)
    ax_pie.set_title(f'{top_store["门店"]} 收入结构', fontsize=14, fontweight='bold')

    # 表格
    table_cols = ['门店', '储值卡销售', '线上团购应收', '其他收入', '总计营业额', '空包率']
    table_df = revenue_df_for_chart[table_cols].copy()
    for col in ['储值卡销售', '线上团购应收', '其他收入', '总计营业额']:
        table_df[col] = (table_df[col]/10).round(0).astype(int)
    ax_table.axis('off')
    table = ax_table.table(cellText=table_df.values, colLabels=table_cols, loc='upper center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.3)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#404040')
            cell.set_text_props(color='white', fontweight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#F5F5F5')

    # 空包率折线图
    vacancy_nums = [float(r.replace('%', '')) for r in vacancy_rates]
    ax_line.plot(x, vacancy_nums, marker='o', linewidth=2, markersize=6, color='#2ECC40')
    ax_line.set_xlabel('门店', fontsize=12)
    ax_line.set_ylabel('空包率 (%)', fontsize=12)
    ax_line.set_title('各门店空包率分析', fontsize=14, fontweight='bold')
    ax_line.set_xticks(x)
    ax_line.set_xticklabels(stores, rotation=45, ha='right', fontsize=9)
    ax_line.grid(True, alpha=0.3)
    for i, v in enumerate(vacancy_nums):
        ax_line.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(REVENUE_CHART, dpi=150, bbox_inches='tight', facecolor='white')
    
    archive_file2 = f'{ARCHIVE_DIR_QINGZHOU}/收入分析综合图_{yesterday}.png'
    plt.savefig(archive_file2, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ 收入分析综合图已保存: {REVENUE_CHART}")
    plt.close()


if __name__ == "__main__":
    print("=" * 50)
    print("开始生成储值率分析和收入分析图表（改进版）")
    print("=" * 50)
    generate_charts()
    print("\n" + "=" * 50)
    print("✅ 图表生成完成！")
    print("=" * 50)
