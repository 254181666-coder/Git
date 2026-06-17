"""
日报分析标签页 (Tab4)
包含：收入结构分析、空包率分析、各时段储值率分析
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, Dict

from src.database import query
from src.utils import plot_chart, simplify_store_name


class QingZhouDailyAPI:
    def __init__(self):
        pass

    def _calc_card_level(self, drink_total: float) -> str:
        """根据酒水变动金额计算卡级"""
        if drink_total <= 0 or drink_total is None:
            return '注册会员'
        elif drink_total < 1000:
            return '500卡'
        elif drink_total < 1500:
            return '1000卡'
        elif drink_total < 2500:
            return '2000卡'
        elif drink_total < 4000:
            return '3000卡'
        elif drink_total < 8000:
            return '5000卡'
        else:
            return '万卡'

    def get_stored_card_level_data(self, date_str: str) -> Optional[Dict]:
        """获取指定日期的储值卡卡级结构数据（基于酒水变动金额计算卡级）"""
        sql = """
            SELECT s.store_name, sv.member_level,
                   COALESCE(sv.drink_principal, 0) + COALESCE(sv.drink_gift, 0) as drink_total,
                   sv.stored_amount, sv.payment_amount
            FROM stored_value sv
            JOIN stores s ON s.id = sv.store_id
            WHERE sv.data_date = ?
        """
        df = query(sql, [date_str])
        if df.empty:
            return None

        df['store_name'] = df['store_name'].apply(simplify_store_name)
        df = df[df['store_name'].notna()]

        df['card_level'] = df['drink_total'].apply(self._calc_card_level)

        level_order = ['注册会员', '500卡', '1000卡', '2000卡', '3000卡', '5000卡', '万卡']
        df['card_level'] = pd.Categorical(df['card_level'], categories=level_order, ordered=True)

        level_df = df.copy()

        return {
            'level_df': level_df,
            'total_by_level': level_df.groupby('card_level', observed=True).agg({
                'stored_amount': 'count',
                'drink_total': 'sum'
            }).reset_index()
        }

    def get_available_dates(self) -> list:
        dates = query(
            "SELECT DISTINCT sd.data_date FROM store_daily sd "
            "JOIN stores s ON sd.store_id = s.id "
            "WHERE sd.total_revenue IS NOT NULL AND sd.total_revenue > 0 "
            "AND sd.data_date IN (SELECT DISTINCT data_date FROM stored_value WHERE stored_amount > 0) "
            "ORDER BY sd.data_date DESC"
        )['data_date'].tolist()
        return dates if dates else []

    def get_daily_analysis(self, date_str: str) -> Optional[Dict]:
        store_df = query(
            "SELECT s.store_name, sd.data_date, sd.total_revenue, sd.stored_card_sales, "
            "sd.online_groupbuy, sd.other_revenue, sd.customers, sd.customers_before_18, "
            "sd.customers_18_to_24, sd.customers_after_00, sd.peak_room_count, "
            "sd.supermarket_revenue, sd.room_revenue, sd.times_card_sales "
            "FROM store_daily sd JOIN stores s ON s.id = sd.store_id "
            "WHERE sd.data_date = ? ORDER BY sd.total_revenue DESC",
            [date_str]
        )
        store_df = store_df.rename(columns={
            'other_revenue': '营业外', 'customers': '全天待客台数',
            'customers_before_18': '18点前待客', 'customers_18_to_24': '18点-24点待客',
            'customers_after_00': '00点后待客', 'peak_room_count': '晚场待客最高峰台数',
            'supermarket_revenue': '超市收入', 'room_revenue': '房费收入',
            'times_card_sales': '次卡销售'
        })

        recharge_df = query(
            "SELECT s.store_name, sv.data_date, sv.member_level, sv.payment_amount, sv.recharge_time "
            "FROM stored_value sv JOIN stores s ON s.id = sv.store_id WHERE sv.data_date = ?",
            [date_str]
        )
        recharge_df = recharge_df.rename(columns={
            'payment_amount': '支付金额', 'recharge_time': '充值时间'
        })

        income_df = store_df.copy()
        room_count_df = query("SELECT store_name, room_count FROM store_room_count")

        if store_df.empty:
            return None

        store_df['门店'] = store_df['store_name'].apply(simplify_store_name)
        store_df = store_df[store_df['门店'].notna()]

        if not recharge_df.empty:
            recharge_df['充值门店'] = recharge_df['store_name'].apply(simplify_store_name)
            recharge_df = recharge_df[recharge_df['充值门店'].notna()]
            recharge_df['小时'] = pd.to_datetime(recharge_df['充值时间'], errors='coerce').dt.hour
            recharge_df['18点前储值'] = recharge_df['小时'].apply(lambda h: 1 if pd.notna(h) and 8 <= h < 18 else 0)
            recharge_df['18-24点储值'] = recharge_df['小时'].apply(lambda h: 1 if pd.notna(h) and 18 <= h < 24 else 0)
            recharge_df['00点后储值'] = recharge_df['小时'].apply(lambda h: 1 if pd.notna(h) and 0 <= h < 8 else 0)
        else:
            for col in ['18点前储值', '18-24点储值', '00点后储值']:
                recharge_df[col] = 0

        if not recharge_df.empty:
            recharge_agg = recharge_df.groupby('充值门店').agg({
                '支付金额': ['count', 'sum'],
                '18点前储值': 'sum', '18-24点储值': 'sum', '00点后储值': 'sum'
            }).reset_index()
            recharge_agg.columns = ['门店', '总储值次数', '充值总金额', '18点前储值', '18-24点储值', '00点后储值']
        else:
            recharge_agg = pd.DataFrame(columns=['门店', '总储值次数', '充值总金额', '18点前储值', '18-24点储值', '00点后储值'])

        store_stores = store_df['门店'].tolist()

        def find_best_match(recharge_store, store_list):
            for s in store_list:
                if s in recharge_store or recharge_store in s:
                    return s
            return recharge_store

        if not recharge_agg.empty:
            recharge_agg['门店'] = recharge_agg['门店'].apply(lambda x: find_best_match(x, store_stores))

        merged = pd.merge(
            store_df[['门店', '全天待客台数', '18点前待客', '18点-24点待客', '00点后待客']],
            recharge_agg, on='门店', how='left'
        ).fillna(0)

        for col in ['全天待客台数', '18点前待客', '18点-24点待客', '00点后待客',
                   '总储值次数', '充值总金额', '18点前储值', '18-24点储值', '00点后储值']:
            if col in merged.columns and merged[col].dtype == 'float64':
                merged[col] = merged[col].astype(int)

        merged['18点前储值率'] = (merged['18点前储值'] / merged['18点前待客'].replace(0, 1) * 100).round(1).replace(float('inf'), 0)
        merged['18-24点储值率'] = (merged['18-24点储值'] / merged['18点-24点待客'].replace(0, 1) * 100).round(1).replace(float('inf'), 0)
        merged['00点后储值率'] = (merged['00点后储值'] / merged['00点后待客'].replace(0, 1) * 100).round(1).replace(float('inf'), 0)
        merged = merged.sort_values('全天待客台数', ascending=False)

        if income_df is not None and not income_df.empty:
            income_summary = income_df[['store_name', 'total_revenue', 'stored_card_sales', 'online_groupbuy',
                                       '营业外', '晚场待客最高峰台数', '全天待客台数']].copy()
            income_summary.columns = ['门店', '总收入', '储值卡', '团购', '其他', '最高峰台数', '接待台数']
            for col in ['总收入', '储值卡', '团购', '其他', '最高峰台数', '接待台数']:
                income_summary[col] = pd.to_numeric(income_summary[col], errors='coerce').fillna(0)
            income_summary['其他'] = (income_summary['总收入'] - income_summary['储值卡'] - income_summary['团购']).clip(lower=0)
        else:
            income_summary = pd.DataFrame()

        chart_data = {
            'x': merged['门店'].tolist(),
            'stores': merged['门店'].tolist(),
            'before_18': merged['18点前储值率'].tolist(),
            'between_18_24': merged['18-24点储值率'].tolist(),
            'after_00': merged['00点后储值率'].tolist()
        }

        table_data = merged[['门店', '全天待客台数', '总储值次数', '充值总金额', '18点前待客', '18点前储值', '18点前储值率',
                            '18点-24点待客', '18-24点储值', '18-24点储值率',
                            '00点后待客', '00点后储值', '00点后储值率']].copy()

        return {
            'chart_data': chart_data,
            'table_data': table_data,
            'merged_df': merged,
            'income_table_data': income_summary if not income_summary.empty else None,
            'room_count_df': room_count_df
        }


def render(qingzhou_api, qingzhou_date_str: str, qingzhou_available_dates: list):
    st.header("📊 日报分析")
    st.caption(f"当前日期: {qingzhou_date_str}, 可用日期数: {len(qingzhou_available_dates)}")

    if not qingzhou_available_dates:
        st.warning("⚠️ 数据库中没有可用的日期数据")
        return

    result = qingzhou_api.get_daily_analysis(qingzhou_date_str)

    if result is None:
        st.warning(f"⚠️ 未找到 {qingzhou_date_str} 的数据")
        return

    chart_data = result['chart_data']
    table_data = result['table_data']
    income_table_data = result.get('income_table_data')

    st.subheader("📊 各门店不同时段储值率分析")

    x = chart_data['x']
    before_18 = chart_data['before_18']
    between_18_24 = chart_data['between_18_24']
    after_00 = chart_data['after_00']

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=before_18, name='18点前储值率', marker_color='#FF4136',
        text=[f'{v:.1f}%' if v > 0 else '' for v in before_18], textposition='outside', textfont=dict(size=10)))
    fig.add_trace(go.Bar(x=x, y=between_18_24, name='18点-24点储值率', marker_color='#FFDC00',
        text=[f'{v:.1f}%' if v > 0 else '' for v in between_18_24], textposition='outside', textfont=dict(size=10)))
    fig.add_trace(go.Bar(x=x, y=after_00, name='00点后储值率', marker_color='#0074D9',
        text=[f'{v:.1f}%' if v > 0 else '' for v in after_00], textposition='outside', textfont=dict(size=10)))

    fig.update_layout(barmode='group', xaxis_title='门店', yaxis_title='储值率 (%)',
        title=f'各门店不同时段储值率分析 (日期: {qingzhou_date_str})',
        template='plotly_white', height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=40), xaxis={'tickangle': -45})
    plot_chart(fig)

    st.divider()
    st.subheader("📋 储值卡汇总数据表")
    st.dataframe(table_data, width='stretch', hide_index=True)

    if income_table_data is not None and not income_table_data.empty:
        st.divider()
        st.subheader("💰 各门店收入结构分析")

        col_layout = st.columns([2, 1])
        with col_layout[0]:
            fig_stacked = go.Figure()
            fig_stacked.add_trace(go.Bar(x=income_table_data['门店'], y=income_table_data['储值卡'], name='储值卡销售', marker_color='#FF4136'))
            fig_stacked.add_trace(go.Bar(x=income_table_data['门店'], y=income_table_data['团购'], name='团购收入', marker_color='#FFDC00'))
            fig_stacked.add_trace(go.Bar(x=income_table_data['门店'], y=income_table_data['其他'], name='其他收入', marker_color='#0074D9'))
            fig_stacked.update_layout(barmode='stack', xaxis_title='门店', yaxis_title='金额(元)',
                title='各门店收入结构堆积图', template='plotly_white', height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            plot_chart(fig_stacked)

        with col_layout[1]:
            top_store = income_table_data.loc[income_table_data['总收入'].idxmax()]
            total_stored = top_store['储值卡']
            total_group = top_store['团购']
            total_other = top_store['其他']
            total_all = total_stored + total_group + total_other
            pie_title = f"{top_store['门店']} 收入结构"
            if total_all > 0:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['储值卡销售', '团购', '其他收入'],
                    values=[total_stored, total_group, total_other],
                    hole=0.4, textinfo='percent+label', textfont_size=12,
                    marker_colors=['#FF4136', '#FFDC00', '#0074D9'])])
                fig_pie.update_layout(title=pie_title, template='plotly_white', height=450, showlegend=False)
                plot_chart(fig_pie)

        st.divider()
        room_df = result.get('room_count_df', pd.DataFrame())
        room_dict = dict(zip(room_df['store_name'], room_df['room_count'])) if not room_df.empty else {}

        display_rows = []
        for _, row in income_table_data.iterrows():
            store = row['门店']
            room_count = room_dict.get(store, 30)
            peak_count = int(row.get('最高峰台数', 0))
            empty_rate = max(0, round((1 - peak_count / room_count) * 100, 1)) if room_count > 0 else 0
            display_rows.append({
                '门店': store,
                '储值卡销售': f"{int(row.get('储值卡', 0)):,}",
                '线上团购进店': f"{int(row.get('团购', 0)):,}",
                '接待客人': f"{int(row.get('接待台数', 0)):,}",
                '总开房数': room_count,
                '空包率': f"{empty_rate:.1f}%"
            })
        st.dataframe(pd.DataFrame(display_rows), width='stretch', hide_index=True)

        st.divider()
        empty_rates = [float(r['空包率'].replace('%', '')) for r in display_rows]
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=income_table_data['门店'], y=empty_rates, mode='lines+markers+text',
            text=[f'{r:.1f}%' for r in empty_rates], textposition='top center',
            line=dict(color='#2ECC40', width=2), marker=dict(size=8, color='#2ECC40')))
        fig_line.update_layout(title='各门店空包率分析', xaxis_title='门店', yaxis_title='空包率 (%)',
            template='plotly_white', height=400)
        plot_chart(fig_line)

    st.divider()
    st.subheader("💳 储值卡卡级结构分析")

    level_data = qingzhou_api.get_stored_card_level_data(qingzhou_date_str)

    if level_data is None or level_data['level_df'].empty:
        st.info("暂无储值卡卡级数据")
    else:
        level_df = level_data['level_df']
        total_by_level = level_data['total_by_level']

        available_stores = ['全部门店'] + sorted(level_df['store_name'].unique().tolist())
        selected_store = st.selectbox("选择门店", available_stores, key="stored_card_store_select")

        CARD_LEVEL_COLORS = {
            '注册会员': '#AAAAAA', '500卡': '#FF4136', '1000卡': '#FF851B',
            '2000卡': '#FFDC00', '3000卡': '#2ECC40', '5000卡': '#0074D9', '万卡': '#B10DC9'
        }

        if selected_store != '全部门店':
            store_level_df = level_df[level_df['store_name'] == selected_store]
            store_total = store_level_df.groupby('card_level', observed=True).agg({
                'drink_total': ['count', 'sum']
            }).reset_index()
            store_total.columns = ['card_level', 'count', 'drink_total']

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{selected_store} 各卡级数量分布**")
                if not store_total.empty:
                    pie_colors = [CARD_LEVEL_COLORS.get(l, '#AAAAAA') for l in store_total['card_level']]
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=store_total['card_level'].astype(str),
                        values=store_total['count'],
                        hole=0.4,
                        textinfo='percent+label',
                        textfont_size=11,
                        marker=dict(colors=pie_colors)
                    )])
                    fig_pie.update_layout(template='plotly_white', height=350, showlegend=True)
                    plot_chart(fig_pie)
                else:
                    st.info("该门店暂无数据")

            with col2:
                st.write(f"**{selected_store} 各卡级酒水金额分布**")
                if not store_total.empty:
                    fig_bar = px.bar(
                        store_total,
                        x='card_level',
                        y='drink_total',
                        text_auto=True,
                        color='card_level',
                        color_discrete_map=CARD_LEVEL_COLORS
                    )
                    fig_bar.update_layout(template='plotly_white', height=350, showlegend=False,
                        xaxis_title='卡级', yaxis_title='酒水变动金额(元)')
                    fig_bar.update_traces(texttemplate='%{y:,.0f}', width=0.6)
                    plot_chart(fig_bar)
                else:
                    st.info("该门店暂无数据")

            st.divider()
            st.write(f"**{selected_store} 卡级明细**")
            store_detail = store_level_df.groupby('card_level', observed=True).agg({
                'drink_total': ['count', 'sum']
            }).reset_index()
            store_detail.columns = ['卡级', '储值次数', '酒水金额']
            store_detail['酒水金额'] = store_detail['酒水金额'].apply(lambda x: f"¥{x:,.2f}")
            st.dataframe(store_detail, width='stretch', hide_index=True)

        else:
            col1, col2 = st.columns(2)

            with col1:
                st.write("**全部门店 各卡级数量分布（基于酒水变动金额）**")
                pie_colors = [CARD_LEVEL_COLORS.get(l, '#AAAAAA') for l in total_by_level['card_level']]
                fig_pie = go.Figure(data=[go.Pie(
                    labels=total_by_level['card_level'].astype(str),
                    values=total_by_level['stored_amount'],
                    hole=0.4,
                    textinfo='percent+label',
                    textfont_size=11,
                    marker=dict(colors=pie_colors)
                )])
                fig_pie.update_layout(template='plotly_white', height=350, showlegend=True)
                plot_chart(fig_pie)

            with col2:
                st.write("**全部门店 各卡级酒水金额分布**")
                fig_bar = px.bar(
                    total_by_level,
                    x='card_level',
                    y='drink_total',
                    text_auto=True,
                    color='card_level',
                    color_discrete_map=CARD_LEVEL_COLORS
                )
                fig_bar.update_layout(template='plotly_white', height=350, showlegend=False,
                    xaxis_title='卡级', yaxis_title='酒水变动金额(元)')
                fig_bar.update_traces(texttemplate='%{y:,.0f}', width=0.6)
                plot_chart(fig_bar)

            st.write("**各门店卡级构成对比（基于酒水变动金额）**")
            store_pivot = level_df.pivot_table(
                index='store_name',
                columns='card_level',
                values='drink_total',
                fill_value=0,
                aggfunc='count'
            ).reset_index()

            fig_stacked = go.Figure()
            colors = ['#AAAAAA', '#FF4136', '#FF851B', '#FFDC00', '#2ECC40', '#0074D9', '#B10DC9']
            for i, level in enumerate(['注册会员', '500卡', '1000卡', '2000卡', '3000卡', '5000卡', '万卡']):
                if level in store_pivot.columns:
                    fig_stacked.add_trace(go.Bar(
                        name=level,
                        x=store_pivot['store_name'],
                        y=store_pivot[level],
                        marker_color=colors[i]
                    ))

            fig_stacked.update_layout(
                barmode='stack',
                template='plotly_white',
                height=400,
                xaxis_title='门店',
                yaxis_title='储值次数',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            plot_chart(fig_stacked)

            st.divider()
            st.write("**各门店卡级明细（基于酒水变动金额）**")
            level_detail = level_df.groupby(['store_name', 'card_level'], observed=True).agg({
                'drink_total': ['count', 'sum']
            }).reset_index()
            level_detail.columns = ['门店', '卡级', '储值次数', '酒水金额']
            level_detail['酒水金额'] = level_detail['酒水金额'].apply(lambda x: f"¥{x:,.2f}")
            st.dataframe(level_detail, width='stretch', hide_index=True)
