#!/usr/bin/env python3
"""
轻舟日报图表生成脚本（数据库版本）
生成储值率分析图和收入分析综合图
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import query
from src.config import OUTPUT_DIR, ARCHIVE_DIR

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

def clear_extended_attributes(file_path: Path):
    """清除文件的扩展属性，避免访问权限问题"""
    import subprocess
    try:
        subprocess.run(['xattr', '-c', str(file_path)], capture_output=True, check=True)
    except:
        pass


STORE_NAME_MAP = {
    '江南秀': '松原一店',
    '斯堡特': '松原二店',
    '法库': '法库店',
    '上东': '上东店',
}

def unify_store_name(name):
    if not name:
        return None
    name = str(name).strip()
    for old, new in STORE_NAME_MAP.items():
        name = name.replace(old, new)
    name = name.replace('私人订制KTV', '').replace('糖果华庭KTV', '')
    name = name.replace('店', '').strip()
    if name in ['总部', '临河街']:
        return None
    return name if name else None


def get_daily_data(target_date):
    """获取指定日期的营业数据和储值数据"""
    store_daily_sql = """
        SELECT
            s.store_name as orig_name,
            sd.total_revenue,
            sd.stored_card_sales,
            sd.customers_before_18,
            sd.customers_18_to_24,
            sd.customers_after_00,
            sd.peak_room_count,
            sd.online_groupbuy
        FROM store_daily sd
        JOIN stores s ON sd.store_id = s.id
        WHERE sd.data_date = %s
        AND sd.total_revenue > 0
    """
    store_df = query(store_daily_sql, (target_date,))
    store_df['门店'] = store_df['orig_name'].apply(unify_store_name)
    store_df = store_df[store_df['门店'].notna()]

    stored_sql = """
        SELECT
            s.store_name as orig_name,
            COUNT(*) as stored_count,
            SUM(sd.stored_amount) as stored_amount,
            SUM(CASE WHEN CAST(substr(sd.recharge_time, 12, 2) AS INTEGER) >= 9 AND CAST(substr(sd.recharge_time, 12, 2) AS INTEGER) < 18 THEN 1 ELSE 0 END) as before_18,
            SUM(CASE WHEN CAST(substr(sd.recharge_time, 12, 2) AS INTEGER) >= 18 AND CAST(substr(sd.recharge_time, 12, 2) AS INTEGER) < 24 THEN 1 ELSE 0 END) as between_18_24,
            SUM(CASE WHEN CAST(substr(sd.recharge_time, 12, 2) AS INTEGER) < 9 THEN 1 ELSE 0 END) as after_00
        FROM stored_value sd
        JOIN stores s ON sd.store_id = s.id
        WHERE sd.data_date = %s
        AND sd.stored_amount > 0
        GROUP BY s.store_name
    """
    stored_df = query(stored_sql, (target_date,))
    stored_df['门店'] = stored_df['orig_name'].apply(unify_store_name)
    stored_df = stored_df[stored_df['门店'].notna()]

    return store_df, stored_df


def get_room_count():
    """读取包房数"""
    room_file = PROJECT_ROOT / "data" / "source" / "包房数.xlsx"
    if not room_file.exists():
        return pd.DataFrame(columns=['门店', '包房数'])
    room_df = pd.read_excel(room_file)
    room_df.columns = ['门店', '包房数']
    room_df['门店'] = room_df['门店'].apply(unify_store_name)
    room_df = room_df[room_df['门店'].notna()]
    return room_df


def get_card_count(target_date):
    """读取次卡数据"""
    # 去数据导入项目的source目录找文件
    data_import_root = PROJECT_ROOT.parent / "数据导入"
    card_file = data_import_root / "data" / "source"
    card_files = list(card_file.glob("*card*.csv")) + list(card_file.glob("*Card*.csv"))
    if not card_files:
        return pd.DataFrame(columns=['门店', '次卡总数'])

    card_df = pd.read_csv(card_files[0], encoding='gbk')
    card_df = card_df[card_df['变动类型'] == '卡券活动发放']
    card_df['发放门店'] = card_df['发放门店'].apply(unify_store_name)
    card_df = card_df[card_df['发放门店'].notna()]
    card_counts = card_df.groupby('发放门店').size().reset_index(name='次卡总数')
    card_counts.columns = ['门店', '次卡总数']
    return card_counts


def generate_stored_rate_chart(store_df, stored_df, target_date):
    """生成储值率分析图"""
    if store_df.empty:
        print(f"⚠️ {target_date} 无门店数据")
        return None

    room_df = get_room_count()
    card_df = get_card_count(target_date)

    merged = store_df[['门店', 'total_revenue', 'stored_card_sales',
                        'customers_before_18', 'customers_18_to_24', 'customers_after_00',
                        'peak_room_count']].copy()
    
    # 处理stored_df可能为空的情况
    if not stored_df.empty:
        merged = merged.merge(stored_df[['门店', 'stored_count', 'before_18', 'between_18_24', 'after_00']],
                             on='门店', how='left')
    else:
        # 如果stored_df为空，初始化这些列
        merged['stored_count'] = 0
        merged['before_18'] = 0
        merged['between_18_24'] = 0
        merged['after_00'] = 0
    
    merged = merged.merge(room_df, on='门店', how='left')
    merged = merged.merge(card_df, on='门店', how='left')
    merged = merged.fillna(0)

    for col in ['customers_before_18', 'customers_18_to_24', 'customers_after_00',
                'stored_count', 'before_18', 'between_18_24', 'after_00', '次卡总数', '包房数', 'peak_room_count']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0).astype(int)

    merged['全天待客台数'] = merged['customers_before_18'] + merged['customers_18_to_24'] + merged['customers_after_00']
    merged['充值总金额'] = merged['stored_card_sales']
    merged['空包率'] = (1 - merged['peak_room_count'] / merged['包房数'].replace(0, 1)) * 100
    merged['空包率'] = merged['空包率'].clip(lower=0).round(1)

    merged['before_18_rate'] = (merged['before_18'] / merged['customers_before_18'].replace(0, 1) * 100).round(1)
    merged['between_18_24_rate'] = (merged['between_18_24'] / merged['customers_18_to_24'].replace(0, 1) * 100).round(1)
    merged['after_00_rate'] = (merged['after_00'] / merged['customers_after_00'].replace(0, 1) * 100).round(1)
    merged['before_18_rate'] = merged['before_18_rate'].replace(float('inf'), 0)
    merged['between_18_24_rate'] = merged['between_18_24_rate'].replace(float('inf'), 0)
    merged['after_00_rate'] = merged['after_00_rate'].replace(float('inf'), 0)

    merged = merged.sort_values('total_revenue', ascending=False)

    weekday = (datetime.strptime(target_date, '%Y-%m-%d')).weekday()
    weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    date_str = f"{target_date} {weekdays[weekday]}"

    CHART_FILE = f'{OUTPUT_DIR}/{target_date}储值率分析图.png'
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 1, figure=fig, height_ratios=[2, 1])
    ax_chart = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])

    x = range(len(merged))
    width = 0.25
    stores = merged['门店'].tolist()

    bars1 = ax_chart.bar([i - width for i in x], merged['before_18_rate'], width, label='日场(9-17)储值率', color='#FF4136')
    bars2 = ax_chart.bar(x, merged['between_18_24_rate'], width, label='黄金场(18-23)储值率', color='#FFDC00')
    bars3 = ax_chart.bar([i + width for i in x], merged['after_00_rate'], width, label='午夜场(0-8)储值率', color='#0074D9')

    ax_chart.set_xlabel('门店', fontsize=12)
    ax_chart.set_ylabel('储值率 (%)', fontsize=12)
    ax_chart.set_title(f'各门店不同时段储值率分析 (日期: {date_str})', fontsize=14, fontweight='bold')
    ax_chart.set_xticks(x)
    ax_chart.set_xticklabels(stores, rotation=45, ha='right', fontsize=9)
    ax_chart.legend(loc='upper right', fontsize=10)
    max_rate = merged[['before_18_rate', 'between_18_24_rate', 'after_00_rate']].max().max()
    if max_rate > 0:
        ax_chart.set_ylim(0, max_rate * 1.2)
    else:
        ax_chart.set_ylim(0, 50)  # 最小设置一个最小范围

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax_chart.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=7)

    ax_table.axis('off')
    summary_cols = ['门店', '全天待客台数', 'stored_count', '充值总金额', '次卡总数',
                    'customers_before_18', 'before_18', 'before_18_rate',
                    'customers_18_to_24', 'between_18_24', 'between_18_24_rate',
                    'customers_after_00', 'after_00', 'after_00_rate']
    display_df = merged[['门店', '全天待客台数', 'stored_count', '充值总金额', '次卡总数',
                          'customers_before_18', 'before_18', 'before_18_rate',
                          'customers_18_to_24', 'between_18_24', 'between_18_24_rate',
                          'customers_after_00', 'after_00', 'after_00_rate']].copy()
    display_df.columns = ['门店', '全天待客台数', '总储值次数', '充值总金额', '次卡总数',
                          '日场(9-17)', '日场储值', '日场储值率',
                          '黄金场(18-23)', '黄金场储值', '黄金场储值率',
                          '午夜场(0-8)', '午夜场储值', '午夜场储值率']
    display_df['充值总金额'] = display_df['充值总金额'].apply(lambda x: round(x/10, 1) if pd.notna(x) else x)
    table_data = display_df.values.tolist()
    table = ax_table.table(cellText=table_data, colLabels=list(display_df.columns), loc='upper center', cellLoc='center')
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
    plt.close()
    clear_extended_attributes(CHART_FILE)
    print(f"✅ 储值率分析图已保存: {CHART_FILE}")
    return CHART_FILE


def generate_income_chart(store_df, stored_df, target_date):
    """生成收入分析综合图"""
    if store_df.empty:
        print(f"⚠️ {target_date} 无门店数据")
        return None

    room_df = get_room_count()

    merged = store_df[['门店', 'total_revenue', 'stored_card_sales', 'online_groupbuy', 'peak_room_count']].copy()
    merged = merged.merge(room_df, on='门店', how='left')
    merged = merged.fillna(0)

    for col in ['total_revenue', 'stored_card_sales', 'online_groupbuy', 'peak_room_count', '包房数']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)

    merged['其他收入'] = merged['total_revenue'] - merged['stored_card_sales'] - merged['online_groupbuy']
    merged['空包率'] = (1 - merged['peak_room_count'] / merged['包房数'].replace(0, 1)) * 100
    merged['空包率'] = merged['空包率'].clip(lower=0).round(1)
    merged['空包率_str'] = merged['空包率'].apply(lambda x: f'{x:.1f}%')

    merged = merged[merged['total_revenue'] > 0].sort_values('total_revenue', ascending=False)

    stores = merged['门店'].tolist()
    stored_vals = [v/10 for v in merged['stored_card_sales'].tolist()]
    online_vals = [v/10 for v in merged['online_groupbuy'].tolist()]
    other_vals = [v/10 for v in merged['其他收入'].tolist()]
    totals = [v/10 for v in merged['total_revenue'].tolist()]
    vacancy_nums = merged['空包率'].tolist()

    REVENUE_CHART = f'{OUTPUT_DIR}/收入分析综合图_{target_date}.png'
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.5, 1, 1], height_ratios=[1.5, 1])

    ax_bar = fig.add_subplot(gs[0, 0])
    ax_pie = fig.add_subplot(gs[0, 1])
    ax_table = fig.add_subplot(gs[0, 2])
    ax_line = fig.add_subplot(gs[1, :])

    x = range(len(merged))
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

    top_store = merged.iloc[0]
    pie_data = [top_store['stored_card_sales'], top_store['online_groupbuy'], top_store['其他收入']]
    pie_labels = ['储值卡销售', '线上团购应收', '其他收入']
    pie_colors = ['#FF4136', '#FFDC00', '#0074D9']
    ax_pie.pie(pie_data, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%', startangle=90)
    ax_pie.set_title(f'{top_store["门店"]} 收入结构', fontsize=14, fontweight='bold')

    table_df = merged[['门店', 'stored_card_sales', 'online_groupbuy', '其他收入', 'total_revenue', '空包率_str']].copy()
    table_df.columns = ['门店', '储值卡销售', '线上团购应收', '其他收入', '总计营业额', '空包率']
    for col in ['储值卡销售', '线上团购应收', '其他收入', '总计营业额']:
        table_df[col] = (table_df[col]/10).round(0).astype(int)
    ax_table.axis('off')
    table = ax_table.table(cellText=table_df.values, colLabels=list(table_df.columns), loc='upper center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.3)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#404040')
            cell.set_text_props(color='white', fontweight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#F5F5F5')

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
    plt.close()
    clear_extended_attributes(REVENUE_CHART)
    print(f"✅ 收入分析综合图已保存: {REVENUE_CHART}")
    return REVENUE_CHART


def main():
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    if len(sys.argv) > 1:
        target_date = sys.argv[1]

    print(f"📅 生成轻舟日报图表: {target_date}")

    store_df, stored_df = get_daily_data(target_date)

    if store_df.empty:
        print(f"⚠️ {target_date} 无数据")
        return False

    print(f"  门店数: {len(store_df)}")

    chart1 = generate_stored_rate_chart(store_df, stored_df, target_date)
    chart2 = generate_income_chart(store_df, stored_df, target_date)

    if chart1 and chart2:
        print(f"✅ 轻舟日报图表生成完成")
        return True
    else:
        print(f"⚠️ 部分图表生成失败")
        return False


if __name__ == '__main__':
    main()
