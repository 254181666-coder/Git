"""
👥 客户存留/流失分析看板
基于2025年储值客户 + 2026年活动数据分析客户流失情况
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from src.utils import normalize_store_name
from src.components.rfm_analysis import render_rfm_analysis, render_rfm_by_store


def simplify_store(name):
    """简化门店名称（统一为'某某店'格式）"""
    return normalize_store_name(name)


@st.cache_data(ttl=3600)
def load_all_customer_data():
    """加载所有客户数据（带缓存）"""
    from src.database import query
    import pandas as pd

    sql_stored = """SELECT store_id, data_date, member_phone FROM stored_value WHERE member_phone IS NOT NULL AND member_phone != ''"""
    df_stored = query(sql_stored)
    df_stored["data_date"] = pd.to_datetime(df_stored["data_date"])
    df_stored["member_phone"] = df_stored["member_phone"].astype(str)
    df_stored["type"] = "储值"
    df_stored["金额"] = 0

    sql_member_change = """SELECT change_store, change_time, member_phone, change_type, ABS(principal_change) as amount
                          FROM member_balance_change
                          WHERE LENGTH(member_phone) > 6
                          AND change_type IN ('订单支付', '会员合并支出', '手动减少')"""
    df_member = query(sql_member_change)
    df_member["data_date"] = pd.to_datetime(df_member["change_time"]).dt.date
    df_member["data_date"] = pd.to_datetime(df_member["data_date"])
    df_member["member_phone"] = df_member["member_phone"].astype(str)
    df_member["type"] = "消费"
    df_member["金额"] = pd.to_numeric(df_member["amount"], errors='coerce').fillna(0).astype(float)

    df_all = pd.concat([
        df_stored[["store_id", "data_date", "member_phone", "type", "金额"]],
        df_member[["change_store", "data_date", "member_phone", "type", "金额"]].rename(columns={"change_store": "store_id"})
    ], ignore_index=True)

    sql_stores = "SELECT id, store_name FROM stores"
    stores_df = query(sql_stores)
    df_all = df_all.merge(stores_df, left_on='store_id', right_on='id', how='left')
    df_all['门店简化'] = df_all['store_name'].apply(simplify_store)

    return df_all


@st.cache_data(ttl=3600)
def load_member_balance_for_rfm():
    """加载会员余额变动数据用于RFM分析"""
    from src.database import query
    import pandas as pd

    sql = """SELECT id, change_store, change_time, member_phone, change_type, ABS(principal_change) as amount
             FROM member_balance_change
             WHERE LENGTH(member_phone) > 6
             AND change_type IN ('订单支付', '会员合并支出', '手动减少')"""
    df = query(sql)

    df["change_time"] = pd.to_datetime(df["change_time"])
    df["member_phone"] = df["member_phone"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0).astype(float)
    df['门店简化'] = df['change_store'].apply(simplify_store)

    return df


def render():
    """渲染客户存留/流失分析看板"""
    st.header("👥 客户存留/流失分析")

    with st.spinner("加载数据中..."):
        df_all = load_all_customer_data()

    if df_all is None or df_all.empty:
        st.warning("⚠️ 数据库中无数据")
        return

    st.info("📊 数据范围：2025年储值客户 + 2026年1月至今活动（储值+消费）")

    df_2025 = df_all[df_all["data_date"] < "2026-01-01"]
    df_2026 = df_all[df_all["data_date"] >= "2026-01-01"]

    total_2025_customers = df_2025["member_phone"].nunique()
    total_2025_stored = len(df_2025[df_2025["type"] == "储值"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("2025年储值客户", f"{total_2025_customers:,} 人")

    with col2:
        st.metric("2025年储值总额", f"¥{total_2025_stored:,.0f} 笔")

    with col3:
        stores_2026 = df_2026["member_phone"].nunique()
        st.metric("2026年活跃客户", f"{stores_2026:,} 人")

    st.divider()

    df_all['门店简化'] = df_all['store_name'].apply(simplify_store)
    df_2025 = df_all[df_all["data_date"] < "2026-01-01"]
    df_2026 = df_all[df_all["data_date"] >= "2026-01-01"]

    available_stores = sorted(df_2026['门店简化'].dropna().unique())
    st.subheader(f"🏪 门店选择（{len(available_stores)}家门店）")

    selected_store = st.selectbox("选择门店", ["全部门店"] + available_stores, key="customer_store_select")

    if selected_store != "全部门店":
        df_2025_filtered = df_2025[df_2025['门店简化'] == selected_store]
        df_2026_filtered = df_2026[df_2026['门店简化'] == selected_store]
    else:
        df_2025_filtered = df_2025[df_2025['门店简化'].notna()]
        df_2026_filtered = df_2026

    customers_2025 = set(df_2025_filtered['member_phone'].dropna().unique())

    churn_months = 6
    latest_activity_date = df_2026_filtered['data_date'].max()
    cutoff_date = latest_activity_date - pd.DateOffset(months=churn_months)

    df_2026_active = df_2026_filtered[df_2026_filtered['data_date'] >= cutoff_date]
    active_customers = set(df_2026_active['member_phone'].dropna().unique())

    df_2025_counts = df_2025_filtered.groupby('member_phone').size()
    real_members = set(df_2025_counts[df_2025_counts >= 2].index)
    real_members = real_members & customers_2025

    churned_members = real_members - active_customers
    retained_members = real_members & active_customers

    st.divider()
    st.subheader("📊 客户存留/流失概览")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("2025年会员", f"{len(real_members):,}")
    with col2:
        st.metric("近6个月活跃会员", f"{len(retained_members):,}", delta=f"{len(retained_members)/len(real_members)*100:.1f}%" if real_members else "N/A")
    with col3:
        st.metric("流失预警会员", f"{len(churned_members):,}", delta=f"-{len(churned_members)/len(real_members)*100:.1f}%" if real_members else "N/A", delta_color="inverse")
    with col4:
        churn_rate = len(churned_members) / len(real_members) * 100 if real_members else 0
        st.metric("流失率", f"{churn_rate:.1f}%", delta="⚠️ 高" if churn_rate > 50 else "✅ 正常", delta_color="inverse" if churn_rate > 50 else "normal")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 存留 vs 流失占比")

        if real_members:
            labels = ['存留会员', '流失会员']
            values = [len(retained_members), len(churned_members)]
            colors = ['#27ae60', '#e74c3c']

            fig = px.pie(
                names=labels,
                values=values,
                hole=0.4,
                color=labels,
                color_discrete_map={labels[0]: colors[0], labels[1]: colors[1]}
            )
            fig.update_layout(template="plotly_white", height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 各门店会员存留率对比")

        store_stats = []
        for store in available_stores:
            df_2025_store = df_2025[df_2025['门店简化'] == store]

            cust_2025 = set(df_2025_store['member_phone'].dropna().unique())
            df_2025_counts_store = df_2025_store.groupby('member_phone').size()
            real_members_store = set(df_2025_counts_store[df_2025_counts_store >= 2].index)
            real_members_store = real_members_store & cust_2025

            if real_members_store:
                retained = len(real_members_store & active_customers)
                churned = len(real_members_store - active_customers)
                store_stats.append({
                    '门店': store,
                    '2025会员': len(real_members_store),
                    '活跃会员': retained,
                    '流失预警': churned,
                    '存留率': retained / len(real_members_store) * 100
                })

        if store_stats:
            stats_df = pd.DataFrame(store_stats)
            stats_df = stats_df.sort_values('存留率', ascending=False)

            fig = px.bar(
                stats_df, x='门店', y='存留率',
                color='存留率',
                color_continuous_scale='RdYlGn',
                range_color=[0, 100],
                text_auto=True
            )
            fig.update_layout(template="plotly_white", height=300, yaxis_range=[0, 100])
            fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📋 门店会员存留明细")

    if store_stats:
        display_df = pd.DataFrame(store_stats)[['门店', '2025会员', '活跃会员', '流失预警', '存留率']].copy()
        display_df['流失率'] = (100 - display_df['存留率']).round(1)
        display_df['存留率'] = display_df['存留率'].apply(lambda x: f"{x:.1f}%")
        display_df['流失率'] = display_df['流失率'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("**说明:** 会员 = 2025年储值2次及以上的客户。流失预警 = 2025年会员中最近6个月无活动记录的客户。流失率 = 流失预警会员 ÷ 2025年会员 × 100%")

    st.divider()

    st.subheader("📋 流失预警会员详情")
    if churned_members:
        churn_df = pd.DataFrame({
            '会员电话': list(churned_members),
            '状态': '流失预警'
        })
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(churn_df, use_container_width=True, hide_index=True)
        with col2:
            csv = churn_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载流失预警名单",
                data=csv,
                file_name=f"流失预警会员_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info("✅ 暂无流失预警会员")

    st.divider()
    st.subheader("💰 RFM客户价值分析")

    with st.spinner("加载会员余额变动数据..."):
        df_member_balance = load_member_balance_for_rfm()

    if df_member_balance is None or df_member_balance.empty:
        st.warning("没有找到会员余额变动数据，无法进行RFM分析")
    else:
        df_rfm = df_member_balance.copy()
        df_rfm['变动类型'] = df_rfm['change_type']
        df_rfm['变动时间'] = df_rfm['change_time']
        df_rfm['本次变动门店'] = df_rfm['门店简化']
        df_rfm['会员电话'] = df_rfm['member_phone']
        df_rfm['本金(变动)'] = df_rfm['amount']

        if selected_store != "全部门店":
            df_rfm = df_rfm[df_rfm['门店简化'] == selected_store]

        if not df_rfm.empty:
            if selected_store == "全部门店":
                st.subheader("🏪 各门店客户价值横向对比")
                render_rfm_by_store(df_rfm)
                st.divider()
                st.subheader("💰 全部门店汇总RFM分析")
                render_rfm_analysis(df_rfm)
            else:
                render_rfm_analysis(df_rfm)
        else:
            st.warning("没有找到活动数据，无法进行RFM分析")
