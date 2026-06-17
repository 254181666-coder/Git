
"""
📈 同比分析页面
对比2025年与2026年同期数据，分析各项指标变化
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from src.database import query
from src.utils import normalize_store_name


@st.cache_data(ttl=60)
def load_data():
    sql = """
        SELECT sd.data_date, s.store_name,
               COALESCE(sd.total_revenue, sd.revenue) as revenue,
               sd.customers, sd.efficiency, sd.daily_batch_consumption
        FROM store_daily sd
        JOIN stores s ON s.id = sd.store_id
    """
    df_daily = query(sql)
    df_daily['data_date'] = pd.to_datetime(df_daily['data_date'])
    df_daily['revenue'] = pd.to_numeric(df_daily['revenue'], errors='coerce').fillna(0) / 10
    df_daily['efficiency'] = pd.to_numeric(df_daily['efficiency'], errors='coerce').fillna(0) / 10
    df_daily['daily_batch_consumption'] = pd.to_numeric(df_daily['daily_batch_consumption'], errors='coerce').fillna(0) / 10
    df_daily['门店'] = df_daily['store_name'].apply(normalize_store_name)

    sql_sv = """
        SELECT sv.data_date, sv.recharge_time, s.store_name, sv.stored_amount, sv.drink_principal
        FROM stored_value sv
        JOIN stores s ON s.id = sv.store_id
    """
    df_stored = query(sql_sv)
    df_stored['data_date'] = pd.to_datetime(df_stored['data_date'])
    df_stored['recharge_time'] = pd.to_datetime(df_stored['recharge_time'], errors='coerce')
    # 重要：数据库里已经是元了，直接用于卡级判断和展示
    df_stored['stored_amount'] = pd.to_numeric(df_stored['stored_amount'], errors='coerce').fillna(0)
    df_stored['drink_principal'] = pd.to_numeric(df_stored['drink_principal'], errors='coerce').fillna(0)
    df_stored['门店'] = df_stored['store_name'].apply(normalize_store_name)

    return df_daily, df_stored


def get_level_from_amount(amount):
    if pd.isna(amount):
        return "其他"
    if amount < 300:
        return "1-300"
    elif amount < 500:
        return "300-500"
    elif amount < 1000:
        return "500-1000"
    elif amount < 2000:
        return "1000-2000"
    elif amount < 3000:
        return "2000-3000"
    elif amount < 5000:
        return "3000-5000"
    elif amount < 10000:
        return "5000-10000"
    else:
        return "10000+"


def render():
    st.header("📈 同比分析")
    st.info("📊 对比2025年与2026年同期数据，分析各项指标变化")

    with st.spinner("加载数据中..."):
        df_daily, df_stored = load_data()

    if df_daily.empty:
        st.warning("⚠️ 数据库中无数据")
        return

    df_daily = df_daily[df_daily['门店'] != '临河街店']
    df_stored = df_stored[df_stored['门店'] != '临河街店']

    available_stores = sorted(df_daily['门店'].dropna().unique())
    all_stores_option = "全部门店"

    col1, col2 = st.columns(2)
    with col1:
        selected_store = st.selectbox("选择门店", [all_stores_option] + available_stores, key="yoy_store_select")
    with col2:
        selected_month = st.selectbox("选择月份", ["1月", "2月", "3月", "4月", "5月"], key="yoy_month_select")

    month_map = {"1月": 1, "2月": 2, "3月": 3, "4月": 4, "5月": 5}
    month_value = month_map[selected_month]

    st.divider()

    if selected_store != all_stores_option:
        df_daily = df_daily[df_daily['门店'] == selected_store]
        df_stored = df_stored[df_stored['门店'] == selected_store]

    df_daily['年份'] = df_daily['data_date'].dt.year
    df_daily['月份'] = df_daily['data_date'].dt.month
    df_daily['日期'] = df_daily['data_date'].dt.strftime('%m-%d')

    df_daily_filtered = df_daily[df_daily['月份'] == month_value]
    df_25_daily = df_daily_filtered[df_daily_filtered['年份'] == 2025]
    df_26_daily = df_daily_filtered[df_daily_filtered['年份'] == 2026]

    # 储值卡数据：2025年按data_date筛选（recharge_time为NULL），2026年按recharge_time筛选（data_date是导入日期）
    df_stored_25 = df_stored[df_stored['data_date'].dt.year == 2025]
    df_stored_26 = df_stored[df_stored['recharge_time'].dt.year == 2026]

    df_25_stored = df_stored_25[df_stored_25['data_date'].dt.month == month_value].copy()
    df_26_stored = df_stored_26[df_stored_26['recharge_time'].dt.month == month_value].copy()

    # 为展示添加日期列
    df_25_stored['日期'] = df_25_stored['data_date'].dt.strftime('%m-%d')
    df_26_stored['日期'] = df_26_stored['recharge_time'].dt.strftime('%m-%d')

    st.subheader("📊 核心指标同比概览")

    col1, col2, col3, col4 = st.columns(4)

    df_25_daily_by_date = df_25_daily.groupby('日期')['revenue'].sum().reset_index()
    df_26_daily_by_date = df_26_daily.groupby('日期')['revenue'].sum().reset_index()
    df_25_daily_by_date.columns = ['日期', 'revenue_2025']
    df_26_daily_by_date.columns = ['日期', 'revenue_2026']

    comparison_revenue = df_25_daily_by_date.merge(df_26_daily_by_date, on='日期', how='outer').fillna(0).sort_values('日期')
    total_revenue_25 = comparison_revenue['revenue_2025'].sum()
    total_revenue_26 = comparison_revenue['revenue_2026'].sum()
    revenue_change = (total_revenue_26 - total_revenue_25) / total_revenue_25 * 100 if total_revenue_25 > 0 else 0

    with col1:
        st.metric(
            "营业额",
            f"¥{total_revenue_26:,.0f}",
            delta=f"{revenue_change:.1f}%",
            delta_color="normal" if revenue_change >= 0 else "inverse"
        )

    df_25_stored_by_date = df_25_stored.groupby('日期')['stored_amount'].sum().reset_index()
    df_26_stored_by_date = df_26_stored.groupby('日期')['drink_principal'].sum().reset_index()
    df_25_stored_by_date.columns = ['日期', 'stored_amount_2025']
    df_26_stored_by_date.columns = ['日期', 'stored_amount_2026']

    comparison_stored = df_25_stored_by_date.merge(df_26_stored_by_date, on='日期', how='outer').fillna(0).sort_values('日期')
    total_stored_25 = comparison_stored['stored_amount_2025'].sum()
    total_stored_26 = comparison_stored['stored_amount_2026'].sum()
    stored_change = (total_stored_26 - total_stored_25) / total_stored_25 * 100 if total_stored_25 > 0 else 0

    with col2:
        st.metric(
            "储值卡销售",
            f"¥{total_stored_26:,.0f}",
            delta=f"{stored_change:.1f}%",
            delta_color="normal" if stored_change >= 0 else "inverse"
        )

    df_25_customers_by_date = df_25_daily.groupby('日期')['customers'].sum().reset_index()
    df_26_customers_by_date = df_26_daily.groupby('日期')['customers'].sum().reset_index()
    df_25_customers_by_date.columns = ['日期', 'customers_2025']
    df_26_customers_by_date.columns = ['日期', 'customers_2026']

    comparison_customers = df_25_customers_by_date.merge(df_26_customers_by_date, on='日期', how='outer').fillna(0).sort_values('日期')
    total_customers_25 = comparison_customers['customers_2025'].sum()
    total_customers_26 = comparison_customers['customers_2026'].sum()
    customers_change = (total_customers_26 - total_customers_25) / total_customers_25 * 100 if total_customers_25 > 0 else 0

    with col3:
        st.metric(
            "总客流",
            f"{total_customers_26:,}人",
            delta=f"{customers_change:.1f}%",
            delta_color="normal" if customers_change >= 0 else "inverse"
        )

    avg_price_25 = total_revenue_25 / total_customers_25 if total_customers_25 > 0 else 0
    avg_price_26 = total_revenue_26 / total_customers_26 if total_customers_26 > 0 else 0
    avg_price_change = (avg_price_26 - avg_price_25) / avg_price_25 * 100 if avg_price_25 > 0 else 0

    with col4:
        st.metric(
            "客单价",
            f"¥{avg_price_26:.1f}",
            delta=f"{avg_price_change:.1f}%",
            delta_color="normal" if avg_price_change >= 0 else "inverse"
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 营业额趋势对比")
        fig = px.line(
            comparison_revenue,
            x='日期',
            y=['revenue_2025', 'revenue_2026'],
            markers=True,
            title="每日营业额对比",
            color_discrete_map={'revenue_2025': '#1f77b4', 'revenue_2026': '#ff7f0e'}
        )
        fig.update_layout(template="plotly_white", height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"2025年{selected_month}总额：¥{total_revenue_25:,.0f}")
        st.write(f"2026年{selected_month}总额：¥{total_revenue_26:,.0f}")

    with col2:
        st.subheader("💵 客单价趋势对比")
        df_25_daily['客单价'] = df_25_daily.apply(
            lambda x: x['efficiency'] if pd.notna(x['efficiency']) and x['efficiency'] > 0 else (x['revenue'] / x['customers'] if x['customers'] > 0 else 0), axis=1
        )
        df_26_daily['客单价'] = df_26_daily.apply(
            lambda x: x['daily_batch_consumption'] if pd.notna(x['daily_batch_consumption']) and x['daily_batch_consumption'] > 0 else (x['revenue'] / x['customers'] if x['customers'] > 0 else 0), axis=1
        )
        price_trend_25 = df_25_daily.groupby('日期')['客单价'].mean().reset_index()
        price_trend_26 = df_26_daily.groupby('日期')['客单价'].mean().reset_index()
        trend_df = price_trend_25.merge(price_trend_26, on='日期', how='outer', suffixes=('_2025', '_2026')).fillna(0).sort_values('日期')

        fig = px.line(
            trend_df,
            x='日期',
            y=['客单价_2025', '客单价_2026'],
            markers=True,
            title="每日客单价对比",
            color_discrete_map={'客单价_2025': '#1f77b4', '客单价_2026': '#ff7f0e'}
        )
        fig.update_layout(template="plotly_white", height=350)
        st.plotly_chart(fig, use_container_width=True)

        st.write(f"2025年{selected_month}平均客单价：¥{trend_df['客单价_2025'].mean():.1f}")
        st.write(f"2026年{selected_month}平均客单价：¥{trend_df['客单价_2026'].mean():.1f}")

    st.divider()

    st.subheader("💰 储值卡卡级金额同比")
    card_levels = ['1-300', '300-500', '500-1000', '1000-2000', '2000-3000', '3000-5000', '5000-10000', '10000+']

    level_data = []
    amount_by_level_25 = {l: 0 for l in card_levels}
    count_by_level_25 = {l: 0 for l in card_levels}
    amount_by_level_26 = {l: 0 for l in card_levels}
    count_by_level_26 = {l: 0 for l in card_levels}

    for _, row in df_25_stored.iterrows():
        amount = row['stored_amount']
        level = get_level_from_amount(amount)
        if level in amount_by_level_25:
            amount_by_level_25[level] += amount
            count_by_level_25[level] += 1

    for _, row in df_26_stored.iterrows():
        amount = row['drink_principal']
        level = get_level_from_amount(amount)
        if level in amount_by_level_26:
            amount_by_level_26[level] += amount
            count_by_level_26[level] += 1

    for level in card_levels:
        amount_25 = amount_by_level_25[level]
        amount_26 = amount_by_level_26[level]
        change = ((amount_26 - amount_25) / amount_25 * 100) if amount_25 > 0 else 0
        level_data.append({
            '卡级': level,
            '2025年金额': f"¥{amount_25:,.0f}",
            '2026年金额': f"¥{amount_26:,.0f}",
            '金额变化': f"¥{amount_26 - amount_25:,.0f}",
            '金额同比': f"{change:.1f}%" if amount_25 > 0 else "N/A",
            '2025年数量': count_by_level_25[level],
            '2026年数量': count_by_level_26[level],
            '数量变化': count_by_level_26[level] - count_by_level_25[level]
        })

    level_df = pd.DataFrame(level_data)
    st.dataframe(level_df, use_container_width=True, hide_index=True)

    level_chart_data_amount = []
    level_chart_data_count = []
    for level in card_levels:
        level_chart_data_amount.append({
            '卡级': level,
            '年份': '2025年',
            '金额': amount_by_level_25[level]
        })
        level_chart_data_amount.append({
            '卡级': level,
            '年份': '2026年',
            '金额': amount_by_level_26[level]
        })
        level_chart_data_count.append({
            '卡级': level,
            '年份': '2025年',
            '数量': count_by_level_25[level]
        })
        level_chart_data_count.append({
            '卡级': level,
            '年份': '2026年',
            '数量': count_by_level_26[level]
        })

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        fig = px.bar(
            pd.DataFrame(level_chart_data_amount),
            x='卡级',
            y='金额',
            color='年份',
            barmode='group',
            title="各卡级储值金额对比",
            color_discrete_map={'2025年': '#1f77b4', '2026年': '#ff7f0e'}
        )
        fig.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col_chart2:
        fig = px.bar(
            pd.DataFrame(level_chart_data_count),
            x='卡级',
            y='数量',
            color='年份',
            barmode='group',
            title="各卡级储值数量对比",
            color_discrete_map={'2025年': '#1f77b4', '2026年': '#ff7f0e'}
        )
        fig.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)
