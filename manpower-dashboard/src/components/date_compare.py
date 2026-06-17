"""
🔄 日期对比标签页 (Tab5)
- 两组日期段核心指标对比
- 详细对比表格
- 变化率分析
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.database import query
from src.utils import plot_chart
from src.components.business_overview import get_valid_stores


def render(min_date_str: str, max_date_str: str, d1s, d1e, d2s, d2e):
    """渲染日期对比标签页"""
    st.header("🔄 日期对比")

    date1_start = d1s
    date1_end = d1e
    date2_start = d2s
    date2_end = d2e

    st.info(f"基准期: {date1_start} ~ {date1_end}  |  对比期: {date2_start} ~ {date2_end}")

    valid_stores_list = get_valid_stores()
    selected_compare_stores = st.multiselect(
        "选择要对比的门店", options=valid_stores_list, default=valid_stores_list
    )

    compare_button = st.button("开始对比")

    if compare_button:
        if not selected_compare_stores:
            st.warning("请至少选择一个门店")
            return

        date1_start_str = date1_start.strftime("%Y-%m-%d")
        date1_end_str = date1_end.strftime("%Y-%m-%d")
        date2_start_str = date2_start.strftime("%Y-%m-%d")
        date2_end_str = date2_end.strftime("%Y-%m-%d")

        @st.cache_data
        def load_compare_data(start_date, end_date, stores):
            placeholders = ', '.join(['?'] * len(stores))

            store_query = f"""
                SELECT s.store_name, sd.*
                FROM store_daily sd
                JOIN stores s ON sd.store_id = s.id
                WHERE sd.data_date BETWEEN ? AND ?
                  AND s.store_name IN ({placeholders})
            """
            store_df = query(store_query, [start_date, end_date] + stores)

            recharge_query = f"""
                SELECT s.store_name, sv.*
                FROM stored_value sv
                JOIN stores s ON sv.store_id = s.id
                WHERE sv.data_date BETWEEN ? AND ?
                  AND s.store_name IN ({placeholders})
            """
            recharge_df = query(recharge_query, [start_date, end_date] + stores)

            return store_df, recharge_df

        store1_df, recharge1_df = load_compare_data(date1_start_str, date1_end_str, selected_compare_stores)
        store2_df, recharge2_df = load_compare_data(date2_start_str, date2_end_str, selected_compare_stores)

        if store1_df.empty or store2_df.empty:
            st.warning("⚠️ 某些日期范围没有数据")
            return

        def process_data(store_df, recharge_df):
            store_df['门店'] = store_df['store_name'].str.replace('私人订制KTV', '').str.replace('糖果华庭KTV', '')
            store_df = store_df[store_df['门店'] != '总部']

            recharge_df['门店'] = recharge_df['store_name'].str.replace('私人订制KTV', '').str.replace('糖果华庭KTV', '')
            recharge_df = recharge_df[recharge_df['门店'] != '总部']

            def safe_get_hour(time_str):
                try:
                    dt = pd.to_datetime(time_str)
                    return dt.hour
                except:
                    return None

            recharge_df['小时'] = recharge_df['recharge_time'].apply(safe_get_hour)
            recharge_df['18点前储值'] = recharge_df.apply(lambda r: 1 if pd.notna(r['小时']) and 8 <= r['小时'] < 18 else 0, axis=1)
            recharge_df['18点-24点储值'] = recharge_df.apply(lambda r: 1 if pd.notna(r['小时']) and 18 <= r['小时'] < 24 else 0, axis=1)
            recharge_df['00点后储值'] = recharge_df.apply(lambda r: 1 if pd.notna(r['小时']) and 0 <= r['小时'] <= 7 else 0, axis=1)

            store_agg = store_df.groupby('门店').agg({
                'customers': 'sum', 'customers_before_18': 'sum', 'customers_18_to_24': 'sum',
                'customers_after_00': 'sum', 'stored_card_sales': 'sum', 'total_revenue': 'sum',
                'peak_room_count': 'sum'
            }).reset_index()

            recharge_agg = recharge_df.groupby('门店').agg({
                'member_name': 'count', 'drink_principal': 'sum',
                '18点前储值': 'sum', '18点-24点储值': 'sum', '00点后储值': 'sum'
            }).reset_index()

            merged = pd.merge(store_agg, recharge_agg, on='门店', how='left').fillna(0)

            merged = merged.rename(columns={
                'customers': '全天待客', 'customers_before_18': '18点前待客',
                'customers_18_to_24': '18点-24点待客', 'customers_after_00': '00点后代客',
                'stored_card_sales': '储值卡销售', 'total_revenue': '总营收',
                'peak_room_count': '最高峰台数', 'member_name': '总储值次数', 'drink_principal': '储值总金额'
            })

            return merged

        data1 = process_data(store1_df, recharge1_df)
        data2 = process_data(store2_df, recharge2_df)

        compare_df = pd.merge(data1, data2, on='门店', suffixes=('_第一组', '_第二组'), how='outer').fillna(0)

        compare_df['营收变化'] = compare_df['总营收_第二组'] - compare_df['总营收_第一组']
        compare_df['营收变化率'] = (compare_df['营收变化'] / compare_df['总营收_第一组'] * 100).round(1)
        compare_df['待客变化'] = compare_df['全天待客_第二组'] - compare_df['全天待客_第一组']
        compare_df['储值变化'] = compare_df['储值卡销售_第二组'] - compare_df['储值卡销售_第一组']

        st.divider()

        st.subheader("📊 核心指标对比")

        col_a, col_b, col_c, col_d = st.columns(4)

        total_revenue1 = data1['总营收'].sum() / 10
        total_revenue2 = data2['总营收'].sum() / 10
        revenue_change = total_revenue2 - total_revenue1
        revenue_change_pct = (revenue_change / total_revenue1 * 100).round(1) if total_revenue1 > 0 else 0

        with col_a:
            st.metric("总营收", f"¥{total_revenue2:,.0f}", delta=f"{revenue_change:+.0f} ({revenue_change_pct:+.1f}%)")

        total_stored1 = data1['储值卡销售'].sum() / 10
        total_stored2 = data2['储值卡销售'].sum() / 10
        stored_change = total_stored2 - total_stored1
        stored_change_pct = (stored_change / total_stored1 * 100).round(1) if total_stored1 > 0 else 0

        with col_b:
            st.metric("总储值金额", f"¥{total_stored2:,.0f}", delta=f"{stored_change:+.0f} ({stored_change_pct:+.1f}%)")

        total_customers1 = data1['全天待客'].sum()
        total_customers2 = data2['全天待客'].sum()
        customers_change = total_customers2 - total_customers1
        customers_change_pct = (customers_change / total_customers1 * 100).round(1) if total_customers1 > 0 else 0

        with col_c:
            st.metric("总待客台数", f"{total_customers2:,.0f}", delta=f"{customers_change:+.0f} ({customers_change_pct:+.1f}%)")

        days1 = (pd.to_datetime(date1_end) - pd.to_datetime(date1_start)).days + 1
        days2 = (pd.to_datetime(date2_end) - pd.to_datetime(date2_start)).days + 1
        avg_revenue1 = total_revenue1 / days1 if days1 > 0 else 0
        avg_revenue2 = total_revenue2 / days2 if days2 > 0 else 0
        avg_change = avg_revenue2 - avg_revenue1
        avg_change_pct = (avg_change / avg_revenue1 * 100).round(1) if avg_revenue1 > 0 else 0

        with col_d:
            st.metric("日均营收", f"¥{avg_revenue2:,.0f}", delta=f"{avg_change:+.0f} ({avg_change_pct:+.1f}%)")

        st.divider()

        st.subheader("📋 详细对比表")
        display_compare = compare_df.copy()
        for col in ['总营收_第一组', '总营收_第二组', '储值卡销售_第一组', '储值卡销售_第二组', '营收变化']:
            display_compare[col] = display_compare[col].apply(lambda x: f"¥{x:,.0f}")

        st.dataframe(display_compare, width='stretch', hide_index=True)
