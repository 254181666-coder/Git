"""
RFM客户价值分析
基于2026年消费数据分析客户价值
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime


def calculate_rfm(df_consumption, analysis_date):
    """计算RFM指标"""
    df = df_consumption.copy()

    rfm = df.groupby('会员电话').agg({
        '变动时间': lambda x: (analysis_date - x.max()).days,
        '变动类型': 'count',
        '本金(变动)': lambda x: x.abs().sum()
    }).reset_index()

    rfm.columns = ['客户电话', 'R', 'F', 'M']
    rfm['R'] = rfm['R'].fillna(0).astype(int)
    rfm['F'] = rfm['F'].fillna(0).astype(int)
    rfm['M'] = rfm['M'].fillna(0)

    return rfm


def get_rfm_score(r, f, m, r_quantiles, f_quantiles, m_quantiles):
    """计算RFM评分"""
    r_score = 1 if r <= r_quantiles[0.25] else 2 if r <= r_quantiles[0.50] else 3 if r <= r_quantiles[0.75] else 4
    f_score = 1 if f <= f_quantiles[0.25] else 2 if f <= f_quantiles[0.50] else 3 if f <= f_quantiles[0.75] else 4
    m_score = 1 if m <= m_quantiles[0.25] else 2 if m <= m_quantiles[0.50] else 3 if m <= m_quantiles[0.75] else 4
    return r_score, f_score, m_score


def classify_customer(r_score, f_score, m_score):
    """客户分类"""
    if r_score == 4 and f_score <= 2:
        return '流失风险客户'

    total_score = r_score + f_score + m_score

    if total_score >= 10:
        return '高价值客户'
    elif total_score >= 7:
        return '潜力客户'
    elif total_score >= 5:
        return '普通客户'
    else:
        return '低价值客户'


def render_rfm_by_store(df_consumption):
    """按门店展示RFM客户价值对比"""
    st.subheader("📊 各门店客户价值对比")

    analysis_date = df_consumption['变动时间'].max()

    stores = sorted(df_consumption['门店简化'].dropna().unique())

    store_rfm_summary = []
    for store in stores:
        store_df = df_consumption[df_consumption['门店简化'] == store]
        if len(store_df) == 0:
            continue

        store_rfm = calculate_rfm(store_df, analysis_date)
        if store_rfm.empty:
            continue

        r_quantiles = store_rfm['R'].quantile([0.25, 0.50, 0.75])
        f_quantiles = store_rfm['F'].quantile([0.25, 0.50, 0.75])
        m_quantiles = store_rfm['M'].quantile([0.25, 0.50, 0.75])

        store_rfm['R评分'], store_rfm['F评分'], store_rfm['M评分'] = zip(*store_rfm.apply(
            lambda x: get_rfm_score(x['R'], x['F'], x['M'], r_quantiles, f_quantiles, m_quantiles), axis=1
        ))

        store_rfm['客户类型'] = store_rfm.apply(
            lambda x: classify_customer(x['R评分'], x['F评分'], x['M评分']), axis=1
        )

        total = len(store_rfm)
        high_value = len(store_rfm[store_rfm['客户类型'] == '高价值客户'])
        potential = len(store_rfm[store_rfm['客户类型'] == '潜力客户'])
        normal = len(store_rfm[store_rfm['客户类型'] == '普通客户'])
        at_risk = len(store_rfm[store_rfm['客户类型'] == '流失风险客户'])
        low = len(store_rfm[store_rfm['客户类型'] == '低价值客户'])

        store_rfm_summary.append({
            '门店': store,
            '客户数': total,
            '高价值客户': high_value,
            '潜力客户': potential,
            '普通客户': normal,
            '流失风险客户': at_risk,
            '低价值客户': low,
            '高价值占比': high_value / total * 100 if total > 0 else 0,
            '流失风险占比': at_risk / total * 100 if total > 0 else 0,
            '高价值平均频次': store_rfm[store_rfm['客户类型'] == '高价值客户']['F'].mean() if high_value > 0 else 0,
            '高价值平均消费': store_rfm[store_rfm['客户类型'] == '高价值客户']['M'].mean() if high_value > 0 else 0,
            '平均频次': store_rfm['F'].mean() if len(store_rfm) > 0 else 0,
            '平均消费': store_rfm['M'].mean() if len(store_rfm) > 0 else 0
        })

    if not store_rfm_summary:
        st.warning("没有足够的门店数据")
        return

    summary_df = pd.DataFrame(store_rfm_summary)
    summary_df = summary_df.fillna(0)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏪 各门店高价值客户占比对比")
        fig = px.bar(
            summary_df.sort_values('高价值占比', ascending=True),
            y='门店',
            x='高价值占比',
            text_auto=True,
            color='高价值占比',
            color_continuous_scale='RdYlGn',
            range_color=[0, 50],
            orientation='h'
        )
        fig.update_layout(template="plotly_white", height=400, yaxis_title=None, xaxis_title="高价值客户占比 (%)")
        fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⚠️ 各门店流失风险客户占比对比")
        fig = px.bar(
            summary_df.sort_values('流失风险占比', ascending=True),
            y='门店',
            x='流失风险占比',
            text_auto=True,
            color='流失风险占比',
            color_continuous_scale='RdYlGn_r',
            range_color=[0, 50],
            orientation='h'
        )
        fig.update_layout(template="plotly_white", height=400, yaxis_title=None, xaxis_title="流失风险客户占比 (%)")
        fig.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📋 各门店客户类型详细分布")

    customer_types = ['高价值客户', '潜力客户', '普通客户', '流失风险客户', '低价值客户']
    for ct in customer_types:
        if ct not in summary_df.columns:
            summary_df[ct] = 0

    display_cols = ['门店', '客户数'] + customer_types + ['高价值占比', '高价值平均频次', '高价值平均消费', '平均频次', '平均消费']
    available_cols = [c for c in display_cols if c in summary_df.columns]
    display_df = summary_df[available_cols].copy()
    display_df['高价值占比'] = display_df['高价值占比'].apply(lambda x: f"{x:.1f}%")
    display_df['平均频次'] = display_df['平均频次'].apply(lambda x: f"{x:.1f}次")
    display_df['平均消费'] = display_df['平均消费'].apply(lambda x: f"¥{x:,.2f}")
    if '高价值平均频次' in display_df.columns:
        display_df['高价值平均频次'] = display_df['高价值平均频次'].apply(lambda x: f"{x:.1f}次")
    if '高价值平均消费' in display_df.columns:
        display_df['高价值平均消费'] = display_df['高价值平均消费'].apply(lambda x: f"¥{x:,.2f}")
    display_df = display_df.sort_values('客户数', ascending=False)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_rfm_analysis(df_consumption):
    """渲染RFM客户价值分析"""
    st.subheader("📊 RFM客户价值分析")

    analysis_date = df_consumption['变动时间'].max()
    st.info(f"分析基准日期: {analysis_date.strftime('%Y-%m-%d')}")

    with st.spinner("计算RFM指标中..."):
        rfm = calculate_rfm(df_consumption, analysis_date)

    if rfm.empty:
        st.warning("没有足够的消费数据进行分析")
        return

    st.metric("分析客户数", f"{len(rfm):,}")
    st.metric("平均消费频率", f"{rfm['F'].mean():.1f} 次")
    st.metric("平均消费金额", f"¥{rfm['M'].mean():,.2f}")

    r_quantiles = rfm['R'].quantile([0.25, 0.50, 0.75])
    f_quantiles = rfm['F'].quantile([0.25, 0.50, 0.75])
    m_quantiles = rfm['M'].quantile([0.25, 0.50, 0.75])

    rfm['R评分'], rfm['F评分'], rfm['M评分'] = zip(*rfm.apply(
        lambda x: get_rfm_score(x['R'], x['F'], x['M'], r_quantiles, f_quantiles, m_quantiles), axis=1
    ))

    rfm['客户类型'] = rfm.apply(
        lambda x: classify_customer(x['R评分'], x['F评分'], x['M评分']), axis=1
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 客户价值分布")
        customer_type_counts = rfm['客户类型'].value_counts()
        fig = px.pie(
            names=customer_type_counts.index,
            values=customer_type_counts.values,
            hole=0.4,
            color=customer_type_counts.index,
            color_discrete_map={
                '高价值客户': '#27ae60',
                '潜力客户': '#3498db',
                '普通客户': '#95a5a6',
                '流失风险客户': '#e74c3c',
                '低价值客户': '#bdc3c7'
            }
        )
        fig.update_layout(template="plotly_white", height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 各类型客户数量与金额")
        type_summary = rfm.groupby('客户类型').agg({
            '客户电话': 'count',
            'M': 'sum'
        }).reset_index()
        type_summary.columns = ['客户类型', '客户数', '总消费金额']
        type_summary = type_summary.sort_values('总消费金额', ascending=False)

        fig = px.bar(
            type_summary,
            x='客户类型',
            y='总消费金额',
            text_auto=True,
            color='客户类型',
            color_discrete_map={
                '高价值客户': '#27ae60',
                '潜力客户': '#3498db',
                '普通客户': '#95a5a6',
                '流失风险客户': '#e74c3c',
                '低价值客户': '#bdc3c7'
            }
        )
        fig.update_layout(template="plotly_white", height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📋 客户分类明细")

    customer_type_order = ['高价值客户', '潜力客户', '普通客户', '流失风险客户', '低价值客户']
    type_stats = []
    for ctype in customer_type_order:
        ctype_df = rfm[rfm['客户类型'] == ctype]
        if len(ctype_df) > 0:
            type_stats.append({
                '客户类型': ctype,
                '客户数': len(ctype_df),
                '占比': f"{len(ctype_df)/len(rfm)*100:.1f}%",
                '平均消费次数': f"{ctype_df['F'].mean():.1f}",
                '平均消费金额': f"¥{ctype_df['M'].mean():,.2f}",
                '总消费金额': f"¥{ctype_df['M'].sum():,.2f}"
            })

    st.dataframe(pd.DataFrame(type_stats), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🎯 运营建议")

    high_value = rfm[rfm['客户类型'] == '高价值客户']
    at_risk = rfm[rfm['客户类型'] == '流失风险客户']
    low_value = rfm[rfm['客户类型'] == '低价值客户']

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"**高价值客户 ({len(high_value):,})**\n占总消费 {high_value['M'].sum()/rfm['M'].sum()*100:.1f}%\n建议：VIP维护、专属服务")
    with col2:
        st.warning(f"**流失风险客户 ({len(at_risk):,})**\n最近未消费但历史有消费\n建议：挽回营销、优惠推送")
    with col3:
        st.info(f"**低价值客户 ({len(low_value):,})**\n消费频次和金额都低\n建议：激活营销、套餐推荐")
