
"""
👥 人效分析标签页 (Tab3)
- 门店人效排名
- 人效对比图
- 基尼系数分析
- 员工提成TOP5
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List

from src.database import query
from src.utils import plot_chart, normalize_store_name, calculate_gini_coefficient


@st.cache_data
def load_staffing_data():
    df = query("""
        SELECT s.store_name, ss.total_staff_count
        FROM store_staffing_summary ss
        JOIN stores s ON ss.store_id = s.id
    """)
    return df


@st.cache_data
def load_room_count_data():
    df = query("""
        SELECT store_name, room_count
        FROM store_room_count
    """)
    return df


@st.cache_data
def get_commission_data(start_date: str, end_date: str):
    sql_product = """
        SELECT s.store_name, pc.commission_staff as employee_name, SUM(pc.commission_amount) as total_commission
        FROM product_commission pc
        JOIN stores s ON pc.store_id = s.id
        WHERE pc.business_date BETWEEN ? AND ?
        GROUP BY s.store_name, pc.commission_staff
    """
    sql_stored = """
        SELECT s.store_name, sc.commission_staff as employee_name, SUM(sc.commission_amount) as total_commission
        FROM stored_commission sc
        JOIN stores s ON sc.store_id = s.id
        WHERE sc.business_date BETWEEN ? AND ?
        GROUP BY s.store_name, sc.commission_staff
    """
    df_product = query(sql_product, [start_date, end_date])
    df_stored = query(sql_stored, [start_date, end_date])
    return df_product, df_stored


@st.cache_data
def get_commission_gini_by_store(start_date: str, end_date: str):
    df_product, df_stored = get_commission_data(start_date, end_date)

    dfs_to_concat = []
    if not df_product.empty and 'store_name' in df_product.columns:
        dfs_to_concat.append(df_product)
    if not df_stored.empty and 'store_name' in df_stored.columns:
        dfs_to_concat.append(df_stored)

    if not dfs_to_concat:
        return {}

    df_combined = pd.concat(dfs_to_concat, ignore_index=True)

    gini_by_store = {}
    employee_count_by_store = {}

    for _, row in df_combined.iterrows():
        try:
            store_name_val = row['store_name']
            employee_val = row['employee_name']
            comm_val = row['total_commission']

            if pd.isna(store_name_val) or pd.isna(employee_val):
                continue

            normalized = normalize_store_name(store_name_val)
            if normalized and normalized != '临河街店':
                if normalized not in gini_by_store:
                    gini_by_store[normalized] = []
                    employee_count_by_store[normalized] = set()

                comm_val = pd.to_numeric(comm_val, errors='coerce')
                if pd.notna(comm_val):
                    gini_by_store[normalized].append(comm_val)
                    employee_count_by_store[normalized].add(employee_val)
        except Exception:
            continue

    result = {}
    for store, commissions in gini_by_store.items():
        if len(commissions) > 1:
            result[store] = calculate_gini_coefficient(commissions)
        else:
            result[store] = 0.0

    for store in employee_count_by_store:
        result[f"{store}_count"] = len(employee_count_by_store[store])

    return result


@st.cache_data
def get_employee_count_by_store(start_date: str, end_date: str) -> dict:
    sql1 = """
        SELECT s.store_name, pc.commission_staff as employee_name
        FROM product_commission pc
        JOIN stores s ON pc.store_id = s.id
        WHERE pc.business_date BETWEEN ? AND ?
        GROUP BY s.store_name, pc.commission_staff
    """
    sql2 = """
        SELECT s.store_name, sc.commission_staff as employee_name
        FROM stored_commission sc
        JOIN stores s ON sc.store_id = s.id
        WHERE sc.business_date BETWEEN ? AND ?
        GROUP BY s.store_name, sc.commission_staff
    """
    df1 = query(sql1, (start_date, end_date))
    df2 = query(sql2, (start_date, end_date))

    dfs = []
    if not df1.empty and 'store_name' in df1.columns:
        dfs.append(df1)
    if not df2.empty and 'store_name' in df2.columns:
        dfs.append(df2)

    if not dfs:
        return {}

    df_combined = pd.concat(dfs, ignore_index=True)
    df_combined['store_name'] = df_combined['store_name'].apply(
        lambda x: normalize_store_name(x) if pd.notna(x) else ''
    )
    df_combined = df_combined[df_combined['store_name'] != '临河街店']

    result = df_combined.groupby('store_name').agg(
        emp_count=('employee_name', 'nunique')
    ).to_dict()['emp_count']

    return result


def render(revenue_df: pd.DataFrame, staffing_df: pd.DataFrame,
           start_date: str, end_date: str):
    st.header("👥 人效分析")

    if not revenue_df.empty:
        revenue_df = revenue_df[revenue_df['store_name'] != '临河街店']

        store_efficiency = revenue_df.groupby('store_name').agg({
            'revenue': 'sum', 'customers': 'sum'
        }).reset_index()
        store_efficiency.columns = ['门店', '总营业额', '总接待台数']

        employee_count = get_employee_count_by_store(start_date, end_date)
        store_efficiency['有提成人数'] = store_efficiency['门店'].apply(
            lambda x: employee_count.get(normalize_store_name(x), 0)
        )

        store_efficiency['营业额人效'] = store_efficiency.apply(
            lambda x: x['总营业额'] / x['有提成人数'] if x['有提成人数'] > 0 else 0, axis=1
        )
        store_efficiency['接待人效'] = store_efficiency.apply(
            lambda x: x['总接待台数'] / x['有提成人数'] if x['有提成人数'] > 0 else 0, axis=1
        )
        store_efficiency = store_efficiency.sort_values('营业额人效', ascending=False)

        gini_by_store = get_commission_gini_by_store(start_date, end_date)
        store_efficiency['标准化门店'] = store_efficiency['门店'].apply(normalize_store_name)
        store_efficiency['提成基尼系数'] = store_efficiency['标准化门店'].apply(
            lambda x: gini_by_store.get(x, 0.0)
        )
        store_efficiency = store_efficiency.drop('标准化门店', axis=1)

        total_stores = len(store_efficiency)
        top_store = store_efficiency.iloc[0]
        bottom_store = store_efficiency.iloc[-1]
        avg_efficiency = store_efficiency[store_efficiency['有提成人数'] > 0]['营业额人效'].mean()

        benchmark_store = "通辽店"
        benchmark_row = store_efficiency[store_efficiency['门店'] == benchmark_store]
        benchmark_efficiency = benchmark_row['营业额人效'].values[0] if not benchmark_row.empty else avg_efficiency

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总门店数", f"{total_stores}")
        with col2:
            st.metric("人效最高门店", f"{top_store['门店']}")
        with col3:
            st.metric("标杆门店人效", f"¥{benchmark_efficiency:,.0f}/人")
        with col4:
            st.metric("人效最低门店", f"{bottom_store['门店']}")

        st.divider()

        st.subheader("门店人效排名（按营业额人效降序）")
        display_store_eff = store_efficiency.copy()
        display_store_eff['总营业额'] = display_store_eff['总营业额'].apply(lambda x: f"¥{x:,.2f}")
        display_store_eff['营业额人效'] = display_store_eff['营业额人效'].apply(lambda x: f"¥{x:,.0f}/人" if x > 0 else "-")
        display_store_eff['接待人效'] = display_store_eff['接待人效'].apply(lambda x: f"{x:.1f}台/人" if x > 0 else "-")
        display_store_eff['有提成人数'] = display_store_eff['有提成人数'].apply(lambda x: f"{x}人")
        display_store_eff['提成基尼系数'] = display_store_eff['提成基尼系数'].apply(lambda x: f"{x:.4f}")
        display_store_eff.insert(0, '排名', range(1, len(display_store_eff)+1))
        st.dataframe(display_store_eff, width='stretch', hide_index=True)

        st.divider()

        st.subheader("人效对比图")
        fig_efficiency = px.bar(
            store_efficiency, x='门店', y='营业额人效',
            title="各门店营业额人效对比",
            labels={'营业额人效': '营业额人效 (元/人)', '门店': '门店'},
            color='营业额人效', color_continuous_scale='Viridis'
        )
        fig_efficiency.update_layout(template="plotly_white", height=500)
        plot_chart(fig_efficiency)

        st.divider()

        st.subheader("关键发现")
        top_ratio = top_store['营业额人效'] / benchmark_efficiency if benchmark_efficiency > 0 else 0
        bottom_ratio = bottom_store['营业额人效'] / benchmark_efficiency if benchmark_efficiency > 0 else 0
        gini_min = store_efficiency['提成基尼系数'].min()
        gini_max = store_efficiency['提成基尼系数'].max()

        st.markdown(f"""
            - **{top_store['门店']}人效最高**：{top_store['营业额人效']:.0f}元/人，是标杆门店的**{top_ratio*100:.1f}%**
            - **{bottom_store['门店']}人效最低**：仅{bottom_store['营业额人效']:.0f}元/人，仅为标杆门店的**{bottom_ratio*100:.1f}%**
            - 提成基尼系数范围：{gini_min:.4f}~{gini_max:.4f}
        """)

        st.divider()

        st.subheader("标杆门店分析")
        if not benchmark_row.empty:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.metric(f"🏆 {benchmark_store}", f"{int(benchmark_row['有提成人数'].values[0])}人",
                         delta=f"¥{benchmark_efficiency:.0f}元/人")
            with col_b2:
                st.metric(f"📊 {benchmark_store} 总营业额",
                         f"¥{benchmark_row['总营业额'].values[0]:,.2f}",
                         delta=f"{int(benchmark_row['总接待台数'].values[0])} 台")

        st.divider()

        st.subheader("人效最低门店分析")
        col_low1, col_low2 = st.columns(2)
        with col_low1:
            if bottom_store['有提成人数'] > 0 and avg_efficiency > 0:
                delta_value = f"{bottom_store['营业额人效']/avg_efficiency*100:.1f}% 平均"
            else:
                delta_value = "N/A"
            st.metric(f"📉 {bottom_store['门店']}",
                     f"¥{bottom_store['营业额人效']:,.0f}/人" if bottom_store['有提成人数'] > 0 else "-",
                     delta=delta_value)
        with col_low2:
            st.metric(f"📊 {bottom_store['门店']} 总营业额",
                     f"¥{bottom_store['总营业额']:,.2f}",
                     delta=f"{int(bottom_store['总接待台数'])} 台")

        st.subheader("各门店员工提成分析")

        sql_product = """
            SELECT s.store_name, pc.commission_staff as employee_name, SUM(pc.commission_amount) as product_commission
            FROM product_commission pc
            JOIN stores s ON pc.store_id = s.id
            WHERE pc.business_date BETWEEN ? AND ?
            GROUP BY s.store_name, pc.commission_staff
        """
        sql_stored = """
            SELECT s.store_name, sc.commission_staff as employee_name, SUM(sc.commission_amount) as stored_commission
            FROM stored_commission sc
            JOIN stores s ON sc.store_id = s.id
            WHERE sc.business_date BETWEEN ? AND ?
            GROUP BY s.store_name, sc.commission_staff
        """
        df_product = query(sql_product, [start_date, end_date])
        df_stored = query(sql_stored, [start_date, end_date])

        df_product['product_commission'] = pd.to_numeric(df_product['product_commission'], errors='coerce').fillna(0) / 10
        df_stored['stored_commission'] = pd.to_numeric(df_stored['stored_commission'], errors='coerce').fillna(0) / 10

        merged_comm = df_product.merge(df_stored, on=['store_name', 'employee_name'], how='outer').fillna(0)
        merged_comm['总提成'] = merged_comm['product_commission'] + merged_comm['stored_commission']
        merged_comm = merged_comm[merged_comm['store_name'] != '临河街店']

        summary_by_store = merged_comm.groupby('store_name').agg({
            'product_commission': 'sum', 'stored_commission': 'sum', '总提成': 'sum'
        }).reset_index()

        product_comm_total = summary_by_store['product_commission']
        stored_comm_total = summary_by_store['stored_commission']
        total_comm = summary_by_store['总提成']

        display_summary = pd.DataFrame({
            '门店': summary_by_store['store_name'],
            '商品提成总额': product_comm_total,
            '储值卡提成总额': stored_comm_total,
            '总提成': total_comm
        })

        display_summary['商品占比'] = (display_summary['商品提成总额'] / display_summary['总提成'].replace(0, float('nan')) * 100).fillna(0).round(1)
        display_summary['储值占比'] = (display_summary['储值卡提成总额'] / display_summary['总提成'].replace(0, float('nan')) * 100).fillna(0).round(1)
        display_summary = display_summary.sort_values('总提成', ascending=False)

        st.markdown("**📊 各门店提成汇总（商品 vs 储值卡）**")
        output_df = display_summary.copy()
        for col in ['商品提成总额', '储值卡提成总额', '总提成']:
            output_df[col] = output_df[col].apply(lambda x: f"¥{x:,.1f}")
        output_df['商品占比'] = output_df['商品占比'].apply(lambda x: f"{x:.1f}%")
        output_df['储值占比'] = output_df['储值占比'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(output_df, width='stretch', hide_index=True)

        st.divider()

        if not merged_comm.empty:
            st.markdown("**🏆 各门店总提成TOP5（商品+储值卡）**")
            merged_comm['标准化门店'] = merged_comm['store_name'].apply(normalize_store_name)
            for store in sorted(merged_comm['标准化门店'].dropna().unique()):
                store_df = merged_comm[merged_comm['标准化门店'] == store].sort_values('总提成', ascending=False).head(5)
                with st.expander(f"**{store}**"):
                    top5_display = store_df[['employee_name', 'product_commission', 'stored_commission', '总提成']].copy()
                    top5_display.columns = ['员工', '商品提成', '储值卡提成', '总提成']
                    for col in ['商品提成', '储值卡提成', '总提成']:
                        top5_display[col] = top5_display[col].apply(lambda x: f"¥{x:.1f}")
                    st.dataframe(top5_display, width='stretch', hide_index=True)

        if merged_comm.empty:
            st.info("💡 提示：如需查看员工提成详情，请确保已导入人员岗位和提成数据到数据库！")
    else:
        st.warning("⚠️ 未找到经营数据或编制数据")
